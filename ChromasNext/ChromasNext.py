from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, create_model

from lib.Event import PluginEvent
from lib.PluginBase import PluginBase, PluginManifest
from lib.PluginHelper import PluginHelper
from lib.PluginSettingDefinitions import (
    ParagraphSetting,
    PluginSettings,
    SettingsGrid,
    ToggleSetting,
)


BASE_URL = "http://127.0.0.1:43871/api/v1"
STATUS_URL = f"{BASE_URL}/status"
CATALOG_URL = f"{BASE_URL}/catalog"
COMMANDS_URL = f"{BASE_URL}/commands"
EXPECTED_API_VERSION = 1

COVASIFY_BRIDGE_SETTING = "covasify_mode_audio_bridge"
EDL_MEDIA_EVENT_NAME = "edl_mode_media_cue"
_HEALTH_INTERVAL_SECONDS = 10.0

FLAT_EFFECT_ACTION_RESTART_MESSAGE = (
    "EDL is reachable now, but the effect-specific lighting actions were not "
    "registered when this COVAS chat started. Restart the COVAS chat assistant "
    "to rebuild those actions from the current EDL catalog."
)

ColorValue = Union[str, list[int]]


class EmptyParams(BaseModel):
    pass


class SetColorParams(BaseModel):
    target: str
    color: ColorValue
    brightness: Optional[float] = None


class SetEffectParams(BaseModel):
    """Internal normalized effect request sent to EDL."""

    target: str
    effect: str
    colors: Optional[list[ColorValue]] = None
    parameters: Optional[dict[str, object]] = None


class RunModeParams(BaseModel):
    mode: str


def _model_payload(value: object) -> object:
    if value is None or isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)
    legacy_dict = getattr(value, "dict", None)
    if callable(legacy_dict):
        return legacy_dict(exclude_none=True)
    return value


def _friendly_target_map(payload: dict[str, object] | None) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    devices = payload.get("devices")
    if not isinstance(devices, list):
        return {}

    enabled_govee = [
        device
        for device in devices
        if isinstance(device, dict)
        and device.get("provider") == "govee_native"
        and device.get("enabled") is not False
    ]
    single_govee = len(enabled_govee) == 1
    result: dict[str, str] = {}

    for device in devices:
        if not isinstance(device, dict):
            continue
        device_label = str(device.get("label") or "Unnamed device").strip()
        provider = str(device.get("provider") or "")
        targets = device.get("targets")
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            target_id = target.get("id")
            if not isinstance(target_id, str) or not target_id:
                continue
            target_label = str(target.get("label") or target_id).strip()
            target_type = str(target.get("type") or "target")
            if target_type == "whole_device":
                if provider == "govee_native" and single_govee:
                    result[target_id] = "Govee"
                else:
                    result[target_id] = device_label
            else:
                result[target_id] = f"{device_label} {target_label}".strip()
    return result


def _normalise_control_name(value: str) -> str:
    return " ".join(
        "".join(
            character.lower() if character.isalnum() else " "
            for character in str(value)
        ).split()
    )


def _catalog_canonical_target(
    payload: dict[str, object] | None,
    requested: str,
) -> str:
    if not isinstance(payload, dict):
        return requested
    if requested.strip().upper() == "ALL":
        return "ALL"

    devices = payload.get("devices")
    if not isinstance(devices, list):
        return requested

    enabled_govee = [
        device
        for device in devices
        if isinstance(device, dict)
        and device.get("provider") == "govee_native"
        and device.get("enabled") is not False
    ]
    single_govee = len(enabled_govee) == 1

    aliases: dict[str, str] = {}
    ambiguous: set[str] = set()

    def add_alias(alias: str, target_id: str) -> None:
        key = _normalise_control_name(alias)
        if not key or key in ambiguous:
            return
        existing = aliases.get(key)
        if existing is None:
            aliases[key] = target_id
        elif existing != target_id:
            aliases.pop(key, None)
            ambiguous.add(key)

    friendly = _friendly_target_map(payload)
    for device in devices:
        if not isinstance(device, dict):
            continue
        device_label = str(device.get("label") or "").strip()
        provider = str(device.get("provider") or "")
        targets = device.get("targets")
        if not isinstance(targets, list):
            continue

        for target in targets:
            if not isinstance(target, dict):
                continue
            target_id = target.get("id")
            if not isinstance(target_id, str) or not target_id:
                continue

            target_label = str(target.get("label") or "").strip()
            target_type = str(target.get("type") or "target")
            add_alias(target_id, target_id)
            if target_id in friendly:
                add_alias(friendly[target_id], target_id)

            if target_type == "whole_device":
                if device_label:
                    add_alias(device_label, target_id)
                if provider == "govee_native" and single_govee:
                    for alias in (
                        "Govee",
                        "Govee strip",
                        "Govee light strip",
                        "Govee LED strip",
                    ):
                        add_alias(alias, target_id)
            elif device_label and target_label:
                add_alias(f"{device_label} {target_label}", target_id)

    return aliases.get(_normalise_control_name(requested), requested)


def _effect_parameter_names(
    payload: dict[str, object] | None,
    effect_id: str,
) -> set[str] | None:
    if not isinstance(payload, dict):
        return None
    wanted = str(effect_id).strip().upper()
    for effect in effect_entries(payload):
        if str(effect.get("id") or "").strip().upper() != wanted:
            continue
        names = effect.get("parameters")
        if not isinstance(names, list):
            return set()
        return {str(name) for name in names}
    return None


def _effect_owned_parameters(
    payload: dict[str, object] | None,
    effect_id: str,
    value: object,
) -> dict[str, object] | None:
    raw = _model_payload(value)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return raw  # type: ignore[return-value]

    allowed = _effect_parameter_names(payload, effect_id)
    if allowed is None:
        return dict(raw)
    return {name: parameter for name, parameter in raw.items() if name in allowed}


def flat_effect_recovery_note(
    *,
    actions_registered: bool,
    catalog_available_now: bool,
) -> str:
    """Return the v1 recovery instruction for a late-arriving EDL catalog."""
    if actions_registered or not catalog_available_now:
        return ""
    return FLAT_EFFECT_ACTION_RESTART_MESSAGE


def effect_entries(payload: dict[str, object]) -> list[dict[str, object]]:
    control = payload.get("effect_control")
    if not isinstance(control, dict):
        return []
    effects = control.get("effects")
    if not isinstance(effects, list):
        return []
    return [item for item in effects if isinstance(item, dict)]


def effect_entry(payload: dict[str, object], effect_id: str) -> dict[str, object] | None:
    wanted = str(effect_id).strip().upper()
    return next(
        (
            item
            for item in effect_entries(payload)
            if str(item.get("id") or "").strip().upper() == wanted
        ),
        None,
    )


def _parameter_annotation(schema: dict[str, object]) -> object:
    values = schema.get("enum")
    if isinstance(values, list) and values:
        return Literal.__getitem__(tuple(values))
    value_type = schema.get("type")
    if value_type == "number":
        return float
    if value_type == "integer":
        return int
    if value_type == "string":
        return str
    return object


def _parameter_field(
    effect_id: str,
    name: str,
    schema: dict[str, object],
    default: object,
) -> Field:
    pieces = [f"{effect_id}-owned parameter {name}."]
    if default is not None:
        pieces.append(f"EDL default={default} when omitted.")
    kwargs: dict[str, object] = {"description": " ".join(pieces)}
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    exclusive_minimum = schema.get("exclusive_minimum")
    if isinstance(minimum, (int, float)) and not isinstance(minimum, bool):
        kwargs["ge"] = minimum
    if isinstance(maximum, (int, float)) and not isinstance(maximum, bool):
        kwargs["le"] = maximum
    if isinstance(exclusive_minimum, (int, float)) and not isinstance(exclusive_minimum, bool):
        kwargs["gt"] = exclusive_minimum
    return Field(default=None, **kwargs)


def flat_effect_action_model(
    payload: dict[str, object],
    effect_id: str,
) -> type[BaseModel]:
    effect = effect_entry(payload, effect_id)
    if effect is None:
        raise ValueError(f"EDL catalog does not advertise effect {effect_id}")

    effect_id = str(effect.get("id") or "").strip().upper()
    fields: dict[str, tuple[object, object]] = {
        "target": (
            str,
            Field(
                ...,
                description=(
                    "Human EDL control target. Use Keyboard, Mouse, ChromaLink, "
                    "Govee/Govee strip when unambiguous, or a configured device/zone "
                    "name returned by edl_catalog."
                ),
            ),
        )
    }

    colors = effect.get("colors")
    colors = colors if isinstance(colors, dict) else {}
    minimum = colors.get("minimum")
    maximum = colors.get("maximum")
    if not (minimum == 0 and maximum == 0):
        cardinality = (
            str(minimum)
            if minimum == maximum
            else f"{minimum}..{'unbounded' if maximum is None else maximum}"
        )
        color_field = Field(
            ... if isinstance(minimum, int) and minimum > 0 else None,
            description=(
                f"Ordered {effect_id} colour palette; catalog cardinality {cardinality}. "
                "Prefer exact RGB [R,G,B] triplets; #RRGGBB remains accepted."
            ),
        )
        color_type = list[ColorValue]
        if isinstance(minimum, int) and minimum > 0:
            fields["colors"] = (color_type, color_field)
        else:
            fields["colors"] = (Optional[color_type], color_field)

    names = effect.get("parameters")
    names = names if isinstance(names, list) else []
    schemas = effect.get("parameter_schema")
    schemas = schemas if isinstance(schemas, dict) else {}
    defaults = effect.get("defaults")
    defaults = defaults if isinstance(defaults, dict) else {}

    for raw_name in names:
        name = str(raw_name)
        raw_schema = schemas.get(name)
        schema = raw_schema if isinstance(raw_schema, dict) else {}
        annotation = _parameter_annotation(schema)
        fields[name] = (
            Optional[annotation],
            _parameter_field(effect_id, name, schema, defaults.get(name)),
        )

    class _FlatEffectModel(BaseModel):
        class Config:
            extra = "forbid"

    return create_model(
        f"EDL{effect_id.title()}Params",
        __base__=_FlatEffectModel,
        **fields,
    )


def flat_action_description(effect: dict[str, object]) -> str:
    effect_id = str(effect.get("id") or "").strip().upper()
    names = effect.get("parameters")
    names = [str(name) for name in names] if isinstance(names, list) else []
    colors = effect.get("colors")
    colors = colors if isinstance(colors, dict) else {}
    minimum = colors.get("minimum")
    maximum = colors.get("maximum")
    if minimum == 0 and maximum == 0:
        color_text = "This effect takes no colour palette."
    else:
        cardinality = (
            str(minimum)
            if minimum == maximum
            else f"{minimum}..{'unbounded' if maximum is None else maximum}"
        )
        color_text = f"Colour palette cardinality: {cardinality}."
    kind = str(effect.get("kind") or "continuous")
    lifetime = (
        "This is a one-shot temporary trigger and expires back to the current underlying EDL state."
        if kind == "triggered_once"
        else "This remains the direct override until replaced or Stand Down is called."
    )
    parameter_text = ", ".join(names) if names else "none"
    return (
        f"Apply native EDL {effect_id}. {color_text} "
        f"The only legal {effect_id} parameter fields are: {parameter_text}. "
        "Parameters are flat action fields; do not invent a generic parameters object and do not borrow fields from other effects. "
        f"{lifetime} Do not claim success or an active parameter unless this action returns success."
    )


class ChromasNextPlugin(PluginBase):
    """COVAS:NEXT command adapter for Elite Dangerous Lighting."""

    def __init__(self, plugin_manifest: PluginManifest):
        super().__init__(plugin_manifest)
        self._catalog_payload: dict[str, object] | None = None
        self._flat_effect_actions_registered = False
        self._helper = None
        self._edl_health_stop = threading.Event()
        self._edl_health_thread = None

        self.settings_config: PluginSettings | None = PluginSettings(
            key="EliteDangerousLightingPlugin",
            label="Chromas Next",
            icon="lightbulb",
            grids=[
                SettingsGrid(
                    key="status",
                    label="Chromas Next",
                    fields=[
                        ParagraphSetting(
                            key="acceptance_status",
                            label=None,
                            type="paragraph",
                            readonly=True,
                            placeholder=None,
                            content=(
                                "Chromas Next lets COVAS:NEXT control Elite Dangerous Lighting. "
                                "You can ask COVAS to change colours and effects, start lighting scenes and saved Modes, "
                                "check the current lighting setup, or Stand Down and return control to EDL. "
                                "Elite Dangerous Lighting remains in charge of your lighting rules, devices and effects."
                            ),
                        )
                    ],
                ),
                SettingsGrid(
                    key="integrations",
                    label="Integrations",
                    fields=[
                        ToggleSetting(
                            key=COVASIFY_BRIDGE_SETTING,
                            label="Enable Covasify bridge for Mode audio",
                            type="toggle",
                            readonly=False,
                            placeholder=None,
                            default_value=False,
                        ),
                        ParagraphSetting(
                            key="covasify_mode_audio_bridge_help",
                            label=None,
                            type="paragraph",
                            readonly=True,
                            placeholder=None,
                            content=(
                                "When enabled, a saved EDL Mode can also start its associated Spotify track through Covasify. "
                                "Turning this off affects music only — Chromas Next will continue to control EDL lighting normally."
                            ),
                        ),
                    ],
                ),
            ],
        )

    def on_chat_start(self, helper: PluginHelper):
        catalog = self._live_catalog()
        self._flat_effect_actions_registered = catalog is not None

        helper.register_action(
            "edl_status",
            (
                "Check the current live status of the standalone Elite Dangerous Lighting application and its local connection. "
                "Use the returned active targets as current truth; do not substitute remembered EDL availability."
            ),
            EmptyParams,
            self.edl_status,
            "global",
        )
        helper.register_action(
            "edl_catalog",
            (
                "Read the authoritative current Elite Dangerous Lighting control catalog. "
                "It returns human control names, active/configured state, effect IDs, colour cardinality, parameter schemas, defaults and target scope. "
                "Use this result instead of maintaining a duplicate effect/zone capability list inside COVAS."
            ),
            EmptyParams,
            self.edl_catalog,
            "global",
        )
        helper.register_action(
            "edl_set_color",
            (
                "Apply native EDL STATIC lighting. Pass target plus one exact RGB [R,G,B] colour or #RRGGBB compatibility string. "
                "Brightness is a separate optional 0..1 field; do not approximate brightness by changing RGB. "
                "Use human EDL control names such as Keyboard, Mouse, ChromaLink, Govee/Govee strip when unambiguous, or a configured device/zone name from edl_catalog. "
                "Do not claim success unless this action returns success."
            ),
            SetColorParams,
            self.edl_set_color,
            "global",
        )

        # Effect-specific schemas are built from EDL's live catalog at chat start.
        # The generic union-schema edl_set_effect action remains deliberately
        # unregistered.
        if catalog is not None:
            for effect in effect_entries(catalog):
                effect_id = str(effect.get("id") or "").strip().upper()
                if not effect_id or effect_id == "STATIC":
                    continue
                model = flat_effect_action_model(catalog, effect_id)
                helper.register_action(
                    f"edl_{effect_id.lower()}",
                    flat_action_description(effect),
                    model,
                    lambda args, states, eid=effect_id: self._run_flat_effect(
                        eid,
                        args,
                        states,
                    ),
                    "global",
                )

        helper.register_action(
            "edl_stand_down",
            (
                "Release COVAS/operator lighting authority in Elite Dangerous Lighting, stop any active EDL Mode, and immediately return to the current underlying EDL rule state. "
                "Use this whenever the user says Stand Down, release lighting control, clear the lighting override, stop the alert, or return lighting to normal. "
                "Do not claim completion unless this action returns success."
            ),
            EmptyParams,
            self.edl_stand_down,
            "global",
        )
        helper.register_action(
            "edl_run_mode",
            (
                "Run a named Elite Dangerous Lighting Mode from the current live EDL profile. "
                "Chromas Next always owns this single public generic Mode action. "
                "If the Chromas Next Covasify bridge setting is enabled and the Mode returns "
                "an optional media cue, Chromas Next hands that cue to Covasify after EDL "
                "accepts the Mode. With the bridge disabled, the same Mode runs lighting-only."
            ),
            RunModeParams,
            self.edl_run_mode,
            "global",
        )

        self._helper = helper
        self._start_edl_health_reporting()

    def on_chat_stop(self, helper: PluginHelper):
        self._stop_edl_health_reporting()
        self._helper = None

    @staticmethod
    def _get_json(url: str):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=0.8) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _post_json(url: str, payload: dict[str, object]):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=0.8) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _bridge_error(exc: urllib.error.HTTPError) -> dict[str, object] | None:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _live_catalog(self) -> dict[str, object] | None:
        try:
            payload = self._get_json(CATALOG_URL)
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return None
        if not isinstance(payload, dict) or payload.get("service") != "elite-dangerous-lighting":
            return None
        if payload.get("api_version") != EXPECTED_API_VERSION:
            return None
        self._catalog_payload = payload
        return payload

    def _edl_status_core(self, args: EmptyParams, projected_states) -> str:
        try:
            payload = self._get_json(STATUS_URL)
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return (
                f"Elite Dangerous Lighting Chromas Next plugin {self.plugin_manifest.version} "
                "is loaded, but the EDL application connection is not available."
            )

        if not isinstance(payload, dict) or payload.get("service") != "elite-dangerous-lighting":
            return "The EDL endpoint responded, but the response was not from Elite Dangerous Lighting."

        api_version = payload.get("api_version")
        if api_version != EXPECTED_API_VERSION:
            return (
                f"Elite Dangerous Lighting is reachable, but its API version "
                f"{api_version!r} is not compatible with plugin API v{EXPECTED_API_VERSION}."
            )

        if payload.get("bridge") != "ready":
            return "Elite Dangerous Lighting is reachable, but its Chromas Next connection is not ready."

        capabilities = payload.get("capabilities", [])
        readable = ", ".join(str(value) for value in capabilities) if isinstance(capabilities, list) else "status"
        active_targets = payload.get("active_control_targets", [])
        if payload.get("lighting_control_available") and isinstance(active_targets, list):
            active = ", ".join(str(value) for value in active_targets)
            control = f"Direct STATIC lighting control is active now for: {active}."
        else:
            control = "No direct lighting targets are active now; start live lighting on a supported target in EDL."
        return (
            f"Elite Dangerous Lighting is connected through API v{api_version}. "
            f"Available connection capabilities: {readable}. {control}"
        )

    def edl_status(self, args: EmptyParams, projected_states) -> str:
        result = self._edl_status_core(args, projected_states)
        note = self._flat_effect_recovery_note()
        return result if not note else f"{result} {note}"

    @staticmethod
    def _describe_parameter(name: str, schema: object, default: object) -> str:
        if not isinstance(schema, dict):
            return name
        pieces = [name]
        value_type = schema.get("type")
        if value_type:
            pieces.append(str(value_type))
        if "enum" in schema and isinstance(schema["enum"], list):
            pieces.append("{" + ",".join(str(value) for value in schema["enum"]) + "}")
        elif "minimum" in schema or "maximum" in schema:
            lower = schema.get("minimum", "-")
            upper = schema.get("maximum", "+")
            pieces.append(f"[{lower}..{upper}]")
        elif "exclusive_minimum" in schema:
            pieces.append(f">{schema['exclusive_minimum']}")
        if default is not None:
            pieces.append(f"default={default}")
        return " ".join(pieces)

    def _edl_catalog_core(self, args: EmptyParams, projected_states) -> str:
        payload = self._live_catalog()
        if payload is None:
            return "I cannot read the EDL lighting catalog because the EDL connection is unavailable or incompatible."

        devices = payload.get("devices")
        if not isinstance(devices, list):
            return "EDL responded, but its lighting catalog was malformed."

        friendly = _friendly_target_map(payload)
        enabled_govee_count = sum(
            1
            for device in devices
            if isinstance(device, dict)
            and device.get("provider") == "govee_native"
            and device.get("enabled") is not False
        )

        lines = ["Elite Dangerous Lighting authoritative control catalog:", "Targets:"]
        for device in devices:
            if not isinstance(device, dict):
                continue
            label = str(device.get("label") or device.get("id") or "Unnamed device")
            enabled = device.get("enabled")
            device_state = "disabled" if enabled is False else "enabled"
            if device.get("active") is True:
                device_state += ", active now"
            lines.append(f"- {label} [{device_state}]")
            targets = device.get("targets")
            if not isinstance(targets, list):
                continue
            for target in targets:
                if not isinstance(target, dict):
                    continue
                target_id = str(target.get("id") or "")
                control_name = friendly.get(
                    target_id,
                    str(target.get("label") or "Unnamed target"),
                )
                target_type = str(target.get("type") or "target")
                state = "active now" if target.get("active") is True else "configured only"
                if target.get("direct_override") is True:
                    state += ", direct override active"
                lines.append(
                    f"  - control_name={control_name}; type={target_type}; {state}"
                )

        if enabled_govee_count == 1:
            lines.append(
                "Govee whole-device aliases: Govee, Govee strip, Govee light strip. Internal GOVEE_ENHANCED identifiers are implementation details and are not required for control."
            )

        effect_control = payload.get("effect_control")
        if isinstance(effect_control, dict):
            color_input = effect_control.get("color_input")
            if isinstance(color_input, dict):
                component_range = color_input.get("rgb_component_range")
                lines.append(
                    "Colour input: ordered RGB [R,G,B] palette; component range "
                    f"{component_range}; optional HEX {color_input.get('hex_format', '#RRGGBB')}."
                )

            effects = effect_control.get("effects")
            if isinstance(effects, list):
                lines.append("Effects:")
                for effect in effects:
                    if not isinstance(effect, dict):
                        continue
                    effect_id = str(effect.get("id") or "")
                    kind = str(effect.get("kind") or "")
                    colors = effect.get("colors")
                    if isinstance(colors, dict):
                        minimum = colors.get("minimum")
                        maximum = colors.get("maximum")
                        cardinality = (
                            str(minimum)
                            if maximum == minimum
                            else f"{minimum}..{'unbounded' if maximum is None else maximum}"
                        )
                    else:
                        cardinality = "catalog-defined"
                    defaults = effect.get("defaults")
                    defaults = defaults if isinstance(defaults, dict) else {}
                    schemas = effect.get("parameter_schema")
                    schemas = schemas if isinstance(schemas, dict) else {}
                    names = effect.get("parameters")
                    names = names if isinstance(names, list) else []
                    descriptions = [
                        self._describe_parameter(
                            str(name),
                            schemas.get(str(name)),
                            defaults.get(str(name)),
                        )
                        for name in names
                    ]
                    parameter_text = ", ".join(descriptions) if descriptions else "none"
                    scope = str(effect.get("supported_target_scope") or "catalog-defined")
                    lines.append(
                        f"- {effect_id}: kind={kind}; colors={cardinality}; parameters={parameter_text}; target_scope={scope}"
                    )

        active_targets = payload.get("active_control_targets", [])
        active_count = len(active_targets) if isinstance(active_targets, list) else 0
        lines.append(
            f"Current live authority reports {active_count} active controllable target(s). Only targets marked active now can accept a direct command."
        )
        lines.append(
            "This catalog is authoritative for COVAS control; do not substitute remembered target/effect capability data."
        )
        return "\n".join(lines)

    def edl_catalog(self, args: EmptyParams, projected_states) -> str:
        result = self._edl_catalog_core(args, projected_states)
        note = self._flat_effect_recovery_note()
        return result if not note else f"{result} {note}"

    def edl_set_color(self, args: SetColorParams, projected_states) -> str:
        parameters = None
        if args.brightness is not None:
            parameters = {"brightness": args.brightness}
        return self.edl_set_effect(
            SetEffectParams(
                target=args.target,
                effect="STATIC",
                colors=[args.color],
                parameters=parameters,
            ),
            projected_states,
        )

    def edl_set_effect(self, args: BaseModel, projected_states) -> str:
        effect_id = str(args.effect).strip().upper()
        target_id = _catalog_canonical_target(
            self._catalog_payload,
            str(args.target),
        )
        parameters_payload = _effect_owned_parameters(
            self._catalog_payload,
            effect_id,
            getattr(args, "parameters", None),
        )
        try:
            payload = self._post_json(
                COMMANDS_URL,
                {
                    "command": "set_effect",
                    "target": target_id,
                    "effect": effect_id,
                    "colors": getattr(args, "colors", None),
                    "parameters": parameters_payload,
                },
            )
        except urllib.error.HTTPError as exc:
            error = self._bridge_error(exc) or {}
            code = error.get("error")
            message = str(error.get("message") or "EDL rejected the lighting effect.")
            if code == "lighting_not_running":
                return (
                    "EDL is connected, but live lighting is not running yet. "
                    "Start lighting in EDL first."
                )
            if code == "target_not_active":
                return (
                    "EDL cannot apply that effect to the configured target in the "
                    f"current live session: {message}"
                )
            return f"EDL rejected the lighting effect: {message}"
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return (
                "I cannot change the EDL lighting effect because the EDL connection "
                "is not connected."
            )

        if not isinstance(payload, dict) or not payload.get("ok"):
            return "EDL responded to the lighting effect command, but the response was malformed."

        targets = payload.get("targets")
        effect = str(payload.get("effect") or effect_id).upper()
        parameters = payload.get("parameters")
        rgb_values = payload.get("colors")
        friendly = _friendly_target_map(self._catalog_payload)

        if isinstance(targets, list) and len(targets) > 1:
            target_text = f"all {len(targets)} currently active whole target(s)"
        else:
            canonical_target = str(
                payload.get("target")
                or (targets[0] if isinstance(targets, list) and targets else target_id)
            )
            target_text = friendly.get(canonical_target, canonical_target)
            if canonical_target.startswith("GOVEE_ENHANCED::"):
                target_text = friendly.get(canonical_target, "Govee")

        details = []
        if isinstance(rgb_values, list) and rgb_values:
            details.append(f"RGB palette {rgb_values}")
        if isinstance(parameters, dict) and parameters:
            readable = ", ".join(
                f"{key}={value}" for key, value in parameters.items()
            )
            details.append(readable)
        detail_text = f" ({'; '.join(details)})" if details else ""

        if effect in {"REACTIVE", "RIPPLE"}:
            return f"Direct EDL {effect} trigger fired on {target_text}{detail_text}."
        return f"Direct EDL {effect} override active on {target_text}{detail_text}."

    def _flat_effect_recovery_note(self) -> str:
        registered = bool(
            getattr(self, "_flat_effect_actions_registered", False)
        )
        if registered:
            return ""
        catalog = self._live_catalog()
        return flat_effect_recovery_note(
            actions_registered=registered,
            catalog_available_now=catalog is not None,
        )

    def _run_flat_effect(self, effect_id: str, args, projected_states) -> str:
        catalog = self._catalog_payload
        effect = (
            effect_entry(catalog, effect_id)
            if isinstance(catalog, dict)
            else None
        )
        if effect is None:
            return f"EDL no longer advertises {effect_id}; refresh the chat/catalog before using this effect."

        payload = _model_payload(args)
        if not isinstance(payload, dict):
            return f"EDL could not parse the {effect_id} action arguments."

        names = effect.get("parameters")
        names = [str(name) for name in names] if isinstance(names, list) else []
        parameters = {
            name: payload[name]
            for name in names
            if name in payload and payload[name] is not None
        }
        generic = SetEffectParams(
            target=str(payload.get("target") or ""),
            effect=effect_id,
            colors=payload.get("colors"),
            parameters=parameters or None,
        )
        result = self.edl_set_effect(generic, projected_states)
        if result.startswith("Direct EDL "):
            return (
                result
                + f" Only the {effect_id} fields explicitly reported in this result were accepted by EDL; do not claim any other parameter is active."
            )
        return result

    def edl_stand_down(self, args: EmptyParams, projected_states) -> str:
        try:
            payload = self._post_json(COMMANDS_URL, {"command": "stand_down"})
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return "I cannot Stand Down EDL lighting because the EDL connection is not available."

        if not isinstance(payload, dict) or not payload.get("ok"):
            return "EDL responded to Stand Down, but the response was malformed."
        cleared = payload.get("cleared_overrides", 0)
        return (
            f"EDL Stand Down complete. Cleared {cleared} direct lighting override(s); "
            "the current underlying EDL rule state has authority again."
        )

    def _covasify_bridge_enabled(self) -> bool:
        return bool(self.settings.get(COVASIFY_BRIDGE_SETTING, False))

    def _report_edl_health(self, *, online: bool) -> None:
        try:
            self._post_json(
                COMMANDS_URL,
                {
                    "command": "report_covas_runtime",
                    "component": "chromas_next",
                    "online": bool(online),
                    "plugin_version": str(self.plugin_manifest.version),
                    "covasify_bridge_enabled": self._covasify_bridge_enabled(),
                    "mode_action_registered": bool(online),
                },
            )
        except Exception:
            # EDL is optional. Chromas Next must remain loadable and usable from
            # COVAS:NEXT even when the standalone EDL process is not reachable.
            return

    def _edl_health_loop(self) -> None:
        while not self._edl_health_stop.wait(_HEALTH_INTERVAL_SECONDS):
            self._report_edl_health(online=True)

    def _start_edl_health_reporting(self) -> None:
        self._stop_edl_health_reporting(report_offline=False)
        self._edl_health_stop.clear()
        self._report_edl_health(online=True)
        thread = threading.Thread(
            target=self._edl_health_loop,
            name="chromas-next-edl-health",
            daemon=True,
        )
        self._edl_health_thread = thread
        thread.start()

    def _stop_edl_health_reporting(self, *, report_offline: bool = True) -> None:
        self._edl_health_stop.set()
        thread = self._edl_health_thread
        self._edl_health_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        if report_offline:
            self._report_edl_health(online=False)

    def _dispatch_optional_media(self, payload: dict[str, object]) -> bool:
        if not self._covasify_bridge_enabled():
            return False
        cue = payload.get("media_cue")
        if not isinstance(cue, str) or not cue.strip():
            return False
        helper = self._helper
        if helper is None:
            return False
        helper.dispatch_event(
            PluginEvent(
                plugin_event_name=EDL_MEDIA_EVENT_NAME,
                plugin_event_content={
                    "mode": str(payload.get("display_name") or payload.get("mode") or ""),
                    "media_cue": cue.strip(),
                },
            )
        )
        return True

    def edl_run_mode(self, args: RunModeParams, projected_states) -> str:
        try:
            payload = self._post_json(
                COMMANDS_URL,
                {
                    "command": "run_mode",
                    "mode": args.mode,
                },
            )
        except urllib.error.HTTPError as exc:
            error = self._bridge_error(exc) or {}
            code = error.get("error")
            message = str(error.get("message") or "EDL rejected the Mode request.")
            if code == "lighting_not_running":
                return (
                    "EDL is connected, but live lighting is not running yet. "
                    "Start lighting in EDL before requesting a Mode."
                )
            if code == "mode_not_found":
                available = error.get("available_modes")
                if isinstance(available, list) and available:
                    names = ", ".join(str(name) for name in available)
                    return f"EDL has no applied live Mode named {args.mode!r}. Available Modes: {names}."
                return f"EDL has no applied live Mode named {args.mode!r}."
            if code == "mode_active":
                return f"EDL cannot start {args.mode!r} yet: {message}"
            if code == "target_not_active":
                return f"EDL cannot start {args.mode!r} on the current live targets: {message}"
            return f"EDL rejected the Mode request: {message}"
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return "I cannot start the EDL Mode because the EDL connection is not available."

        if not isinstance(payload, dict) or not payload.get("ok"):
            return "EDL responded to the Mode request, but the response was malformed."

        media_dispatched = self._dispatch_optional_media(payload)
        self._report_edl_health(online=True)

        name = str(payload.get("display_name") or payload.get("mode") or args.mode)
        targets = payload.get("targets")
        count = len(targets) if isinstance(targets, list) else 0
        duration = payload.get("duration_seconds")
        try:
            duration_text = f"{float(duration):g}"
        except (TypeError, ValueError):
            duration_text = "bounded"

        if count:
            result = (
                f"EDL Mode {name} started on {count} active lighting target(s) for "
                f"{duration_text} seconds. EDL owns the saved sequence and will restore "
                "the current underlying rule state when it ends."
            )
        else:
            result = (
                f"EDL Mode {name} started for {duration_text} seconds. EDL owns the saved "
                "sequence and will restore the current underlying rule state when it ends."
            )

        if media_dispatched:
            result += " Its optional media cue was handed to the enabled Covasify bridge."
        return result

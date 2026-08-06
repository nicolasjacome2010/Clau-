"""Domain entities for the privacy bounded context.

This context owns the two rights docs/PRD.md §18 and docs/UX_DESIGN.md
Pantalla 12 promise the user in the product itself — "exportar mis datos"
and "borrar todo mi historial" — rather than hiding them in a support
inbox.

It deliberately owns no table of its own. Privacy is not another kind of
data; it is a *view over* everyone else's, so this context reads through
the other contexts' repository interfaces and writes nothing but a
deletion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UserDataExport:
    """Everything the system holds about one user, in one document.

    Each section is a list of plain dicts rather than the owning context's
    entities: an export is a *serialization contract with the user*, and
    coupling it to internal entity shapes would mean a refactor silently
    changing what people receive. The API layer adds no fields of its own.
    """

    exported_at: datetime
    user: dict[str, Any]
    profile: dict[str, Any] | None
    goals: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    simulations: list[dict[str, Any]] = field(default_factory=list)
    decision_outcomes: list[dict[str, Any]] = field(default_factory=list)
    bias_profile: dict[str, Any] | None = None
    memories: list[dict[str, Any]] = field(default_factory=list)
    subscription: dict[str, Any] | None = None

    @property
    def notes(self) -> list[str]:
        """What the export deliberately does not contain, said out loud.

        An export that quietly omits things is worse than one that names
        its own edges: the user can't ask for what they don't know exists.
        """
        return [
            "Los embeddings de memoria se incluyen como texto resumido, no "
            "como vectores: el vector es una representación interna del "
            "mismo texto, no un dato adicional sobre vos.",
            "Los registros de facturación viven en Stripe, que los conserva "
            "por obligación legal (facturación e impuestos). Acá va el "
            "estado de tu suscripción, no tu historial de pagos.",
            "Tu cuenta de acceso (email y credenciales) la administra "
            "Supabase Auth, un sistema separado de esta base de datos.",
        ]

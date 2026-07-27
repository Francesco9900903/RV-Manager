from dataclasses import dataclass
from typing import Optional

@dataclass
class Insight:
    level: str
    title: str
    message: str
    action: Optional[str] = None

def build_personnel_insights(current: dict, previous: dict) -> list[Insight]:
    insights: list[Insight] = []

    current_cost = float(current.get("management_cost") or 0)
    previous_cost = float(previous.get("management_cost") or 0)
    current_incidence = float(current.get("incidence") or 0)
    previous_incidence = float(previous.get("incidence") or 0)
    current_overtime = float(current.get("overtime") or 0)
    previous_overtime = float(previous.get("overtime") or 0)

    if previous_cost:
        delta = (current_cost - previous_cost) / previous_cost * 100
        if delta >= 8:
            insights.append(Insight(
                "warning",
                "Costo personale in aumento",
                f"Il costo gestionale è aumentato del {delta:.1f}% rispetto al mese precedente.",
                "Controlla extra, straordinari e reparto con il maggiore incremento.",
            ))
        elif delta <= -8:
            insights.append(Insight(
                "success",
                "Costo personale in diminuzione",
                f"Il costo gestionale è diminuito del {abs(delta):.1f}% rispetto al mese precedente.",
                "Verifica che la riduzione non dipenda da ore mancanti o dati non ancora caricati.",
            ))

    incidence_delta = current_incidence - previous_incidence
    if current_incidence >= 35:
        insights.append(Insight(
            "critical",
            "Incidenza elevata",
            f"L'incidenza del personale è {current_incidence:.1f}%.",
            "Analizza ore, coperti e costo per reparto prima di programmare i prossimi turni.",
        ))
    elif current_incidence and current_incidence <= 30:
        insights.append(Insight(
            "success",
            "Incidenza sotto controllo",
            f"L'incidenza del personale è {current_incidence:.1f}%.",
        ))
    elif incidence_delta >= 2:
        insights.append(Insight(
            "warning",
            "Incidenza in peggioramento",
            f"L'incidenza è aumentata di {incidence_delta:.1f} punti.",
            "Confronta il calo dei ricavi con l'aumento di ore o costi.",
        ))

    if previous_overtime:
        overtime_delta = (
            (current_overtime - previous_overtime)
            / previous_overtime * 100
        )
        if overtime_delta >= 25:
            insights.append(Insight(
                "warning",
                "Straordinari in forte aumento",
                f"Gli straordinari sono aumentati del {overtime_delta:.1f}%.",
                "Controlla i dipendenti e i reparti che concentrano più ore extra.",
            ))
    elif current_overtime >= 20:
        insights.append(Insight(
            "warning",
            "Straordinari da verificare",
            f"Nel mese risultano {current_overtime:.2f} ore di straordinario.",
        ))

    department_costs = current.get("department_costs") or {}
    if department_costs and current_cost:
        top_department = max(department_costs, key=department_costs.get)
        top_value = float(department_costs[top_department] or 0)
        share = top_value / current_cost * 100
        insights.append(Insight(
            "info",
            "Reparto con il costo maggiore",
            f"{top_department} pesa per il {share:.1f}% del costo personale.",
            "Confronta questo peso con ore lavorate e coperti serviti.",
        ))

    if not insights:
        insights.append(Insight(
            "info",
            "Situazione stabile",
            "Non emergono variazioni rilevanti dai dati disponibili.",
        ))

    return insights

from dataclasses import dataclass


@dataclass
class DashboardReportDTO:
    id: str
    name: str
    sort_order: int

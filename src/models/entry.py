from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Entry:
    date_str: str           # "08/05/26"
    vehicle: str
    vehicle_class: int      # 3 or 4
    odo_start: Optional[int] = None
    odo_end: Optional[int] = None
    mileage: Optional[int] = None

    def derive_missing(self) -> list[str]:
        """Fill the missing field from the other two. Returns list of warnings."""
        warnings = []
        known = sum(x is not None for x in [self.odo_start, self.odo_end, self.mileage])

        if known < 2:
            raise ValueError("Need at least 2 of: start, end, mileage")

        if self.odo_start is not None and self.odo_end is not None and self.mileage is None:
            self.mileage = self.odo_end - self.odo_start
        elif self.odo_start is not None and self.mileage is not None and self.odo_end is None:
            self.odo_end = self.odo_start + self.mileage
        elif self.odo_end is not None and self.mileage is not None and self.odo_start is None:
            self.odo_start = self.odo_end - self.mileage
        elif all(x is not None for x in [self.odo_start, self.odo_end, self.mileage]):
            if self.odo_end - self.odo_start != self.mileage:
                warnings.append(
                    f"Mismatch: {self.odo_end} − {self.odo_start} = "
                    f"{self.odo_end - self.odo_start}, but mileage given as {self.mileage}. "
                    "Using end − start."
                )
                self.mileage = self.odo_end - self.odo_start

        return warnings

    def validate(self) -> list[str]:
        """Returns list of error strings. Empty = valid."""
        errors = []
        if not self.vehicle:
            errors.append("Vehicle number is required.")
        if self.vehicle_class not in (3, 4):
            errors.append("Vehicle class must be 3 or 4.")
        if self.mileage is not None and self.mileage < 0:
            errors.append("End odometer is less than start — did you mix them up?")
        if self.odo_end is not None and self.odo_start is not None and self.odo_end < self.odo_start:
            errors.append("End odometer is less than start — did you mix them up?")
        try:
            d = _parse_date(self.date_str)
            days_ahead = (d - date.today()).days
            if days_ahead > 7:
                errors.append(f"Date is {days_ahead} days in the future — please confirm.")
        except ValueError:
            errors.append(f"Invalid date format: {self.date_str!r}. Use DD/MM/YY.")
        return errors

    def sanity_warnings(self) -> list[str]:
        warnings = []
        if self.mileage is not None and self.mileage > 1000:
            warnings.append(f"Mileage {self.mileage} km is over 1000 km — please confirm.")
        return warnings

    def summary(self) -> str:
        start_str = str(self.odo_start) if self.odo_start is not None else "—"
        end_str = str(self.odo_end) if self.odo_end is not None else "—"
        return (
            f"📅 {self.date_str}\n"
            f"🚗 {self.vehicle}\n"
            f"🏷️ Class {self.vehicle_class}\n"
            f"📍 {start_str} → {end_str}\n"
            f"📏 {self.mileage} km"
        )


def _parse_date(date_str: str) -> date:
    parts = date_str.split("/")
    if len(parts) != 3:
        raise ValueError
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    if year < 100:
        year += 2000
    return date(year, month, day)


def today_str() -> str:
    d = date.today()
    return f"{d.day:02d}/{d.month:02d}/{str(d.year)[2:]}"

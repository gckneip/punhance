from datetime import date

# HomeBank stores dates as GLib GDate julian days: a proleptic-Gregorian
# ordinal where day 1 = 0001-01-01 - the same numbering as Python's
# date.toordinal()/date.fromordinal(). Verified against a real HomeBank
# data point: 2017-05-14 <-> 736463.


def julian_to_date(julian_day: int) -> date:
    return date.fromordinal(julian_day)


def date_to_julian(d: date) -> int:
    return d.toordinal()

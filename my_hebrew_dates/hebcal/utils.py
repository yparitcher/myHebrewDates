from datetime import date

from icalendar import Calendar, Event, Timezone

from .models import Calendar as ModelCalendar
from .models import HebrewDate


def generate_ical(modelCalendar: ModelCalendar):
    newcal = Calendar()
    newcal.add("prodid", "-//" + modelCalendar.name + "//MyHebrewDates.com//")
    newcal.add("version", "2.0")
    newcal.add("x-wr-calname", modelCalendar.name)

    newtimezone = Timezone()
    newtimezone.add("tzid", modelCalendar.timezone)
    newcal.add_component(newtimezone)

    for hebrewDate in modelCalendar.calendarOf.all():
        hebrewDate: HebrewDate = hebrewDate
        for engDate in hebrewDate.get_english_dates():
            engDate: date = engDate
            event = Event()
            event.add("summary", hebrewDate.event_type + " " + hebrewDate.name)
            event.add("dtstart", engDate)
            event.add("dtend", engDate)
            newcal.add_component(event)

    cal_bye_str = newcal.to_ical()
    modelCalendar.calendar_file_str = cal_bye_str.decode("utf8")
    modelCalendar.save()
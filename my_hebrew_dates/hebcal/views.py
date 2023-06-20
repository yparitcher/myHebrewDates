import icalendar
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.db import transaction
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import HebrewDateFormSet
from .models import Calendar
from .utils import generate_ical


class CalendarListView(LoginRequiredMixin, ListView):
    model = Calendar
    login_url = reverse_lazy("login")
    template_name = "hebcal/calendar_list.html"

    def get_queryset(self):
        # Retrieve the calendars belonging to the current user
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        # Call the parent implementation to get the default context
        context = super().get_context_data(**kwargs)
        # Add the domain_name to the context
        context["domain_name"] = Site.objects.get_current().domain

        return context


class CalendarShareView(DeleteView):
    model = Calendar
    template_name = "hebcal/calendar_share.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        # Retrieve the calendar by uuid
        queryset = super().get_queryset()
        return queryset.filter(uuid=self.kwargs["uuid"])

    def get_context_data(self, **kwargs):
        # Call the parent implementation to get the default context
        context = super().get_context_data(**kwargs)
        # Add the domain_name to the context
        context["domain_name"] = Site.objects.get_current().domain
        cal = icalendar.Calendar.from_ical(self.object.calendar_file_str)

        events = []
        for component in cal.walk():
            if component.name == "VEVENT":
                event = {
                    "summary": component.get("summary"),
                    "description": component.get("description")[:-37],
                    "start": component.get("dtstart").dt,
                    "end": component.get("dtend").dt,
                }
                events.append(event)

        # Sort events by start date and time
        events.sort(key=lambda e: e["start"])
        context["events"] = events

        return context


class CalendarCreateView(LoginRequiredMixin, CreateView):
    model = Calendar
    login_url = reverse_lazy("login")
    template_name = "hebcal/calendar_detail.html"
    fields = ["name", "timezone"]

    def get_queryset(self):
        # Retrieve the calendars belonging to the current user
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["hebrewDates"] = HebrewDateFormSet(self.request.POST)
        else:
            data["hebrewDates"] = HebrewDateFormSet()
        data["domain_name"] = Site.objects.get_current().domain
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        hebrewDates = context["hebrewDates"]
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.owner = self.request.user  # Set the owner field
            self.object.save()

            if hebrewDates.is_valid():
                hebrewDates.instance = self.object
                hebrewDates.save()
        return super().form_valid(form)


class CalendarUpdateView(LoginRequiredMixin, UpdateView):
    model = Calendar
    login_url = reverse_lazy("login")
    template_name = "hebcal/calendar_detail.html"
    fields = ["name", "timezone"]

    def get_queryset(self):
        # Retrieve the calendars belonging to the current user
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["hebrewDates"] = HebrewDateFormSet(self.request.POST, instance=self.object)
        else:
            data["hebrewDates"] = HebrewDateFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        hebrewDates = context["hebrewDates"]
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.owner = self.request.user  # Set the owner field
            self.object.save()

            if hebrewDates.is_valid():
                hebrewDates.instance = self.object
                hebrewDates.save()
        return super().form_valid(form)


class CalendarDeleteView(LoginRequiredMixin, DeleteView):
    model = Calendar
    success_url = reverse_lazy("hebcal:calendar_list")
    login_url = reverse_lazy("login")
    template_name = "hebcal/calendar_delete.html"


def calendar_file(request, uuid):
    calendar: Calendar = get_object_or_404(Calendar.objects.filter(uuid=uuid))
    generate_ical(calendar)
    calendar_str: str = calendar.calendar_file_str

    response = HttpResponse(calendar_str, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{uuid}.ics"'

    return response

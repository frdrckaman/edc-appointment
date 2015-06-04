import copy

from datetime import datetime, timedelta

from django.apps import apps as django_apps

from edc_configuration.models import GlobalConfiguration
from edc_visit_schedule.models import VisitDefinition


class AppointmentDateHelper(object):
    """ """
    def __init__(self):
        self.window_delta = None
        # not used
        self.allow_backwards = False
        self.appointments_days_formard = GlobalConfiguration.objects.get_attr_value('appointments_days_forward')
        self.appointments_per_day_max = GlobalConfiguration.objects.get_attr_value('appointments_per_day_max')
        self.use_same_weekday = GlobalConfiguration.objects.get_attr_value('use_same_weekday')
        self.allowed_iso_weekdays = GlobalConfiguration.objects.get_attr_value('allowed_iso_weekdays')

    def get_best_datetime(self, appt_datetime, site, weekday=None, exception_cls=None):
        """ Gets the edc_appointment datetime on insert.

        For example, may be configured to be on the same day as the base, not on holiday, etc.

        Note, appt_datetime comes from the member model method get_registration_datetime"""
        exception_cls = exception_cls or AttributeError
        if weekday and self.use_same_weekday:
            # force to use same week day for every edc_appointment
            appt_datetime = self.move_to_same_weekday(appt_datetime, weekday)
        return self.check_datetime(appt_datetime, site)

    def change_datetime(self, best_appt_datetime, new_appt_datetime, site, visit_definition):
        """Checks if an edc_appointment datetime from the user is OK to change."""
        new_appt_datetime = self.check_datetime(new_appt_datetime, site)
        if not visit_definition.is_datetime_in_window(new_appt_datetime, best_appt_datetime):
            new_appt_datetime = best_appt_datetime
        return new_appt_datetime

    def get_relative_datetime(self, base_appt_datetime, visit_definition):
        """ Returns edc_appointment datetime relative to the base_appointment_datetime."""
        appt_datetime = (
            base_appt_datetime + VisitDefinition.objects.relativedelta_from_base(visit_definition=visit_definition))
        return self.get_best_datetime(appt_datetime, base_appt_datetime.isoweekday())

    def check_datetime(self, appt_datetime, site):
        appt_datetime = self.check_if_allowed_isoweekday(appt_datetime)
        appt_datetime = self.check_if_holiday(appt_datetime)
        appt_datetime = self.move_on_appt_max_exceeded(appt_datetime, site)
        return appt_datetime

    def check_if_allowed_isoweekday(self, appt_datetime):
        """ Checks if weekday is allowed, otherwise adjust forward or backward """
        allowed_iso_weekdays = [int(num) for num in str(self.allowed_iso_weekdays)]
        forward = copy.deepcopy(appt_datetime)
        while forward.isoweekday() not in allowed_iso_weekdays:
            forward = forward + timedelta(days=+1)
        backward = copy.deepcopy(appt_datetime)
        while backward.isoweekday() not in allowed_iso_weekdays:
            backward = backward + timedelta(days=-1)
        # which is closer to the original appt_datetime
        td_forward = abs(appt_datetime - forward)
        td_backward = abs(appt_datetime - backward)
        if td_forward <= td_backward:
            appt_datetime = forward
        else:
            appt_datetime = backward
        return appt_datetime

    def check_if_holiday(self, appt_datetime):
        """ Checks if appt_datetime lands on a holiday, if so, move forward """
        Holiday = django_apps.get_model('edc_appointment', 'holiday')
        while appt_datetime.date() in [holiday.holiday_date for holiday in Holiday.objects.all()]:
            appt_datetime = appt_datetime + timedelta(days=+1)
            appt_datetime = self.check_if_allowed_isoweekday(appt_datetime)
        if not appt_datetime:
            raise TypeError('Appt_datetime cannot be None')
        return appt_datetime

    def move_to_same_weekday(self, appt_datetime, weekday=1):
        """ Moves edc_appointment to use same weekday for each subject edc_appointment."""
        if self.use_same_weekday:
            if weekday not in range(1, 8):
                raise ValueError('Weekday must be a number between 1-7, Got %s' % (weekday, ))
            # make all appointments land on the same isoweekday,
            # if possible as date may change becuase of holiday and/or iso_weekday checks below)
            forward = appt_datetime
            while not forward.isoweekday() == weekday:
                forward = forward + timedelta(days=+1)
            backward = appt_datetime
            while not backward.isoweekday() == weekday:
                backward = backward - timedelta(days=+1)
            # which is closer to the original appt_datetime
            td_forward = abs(appt_datetime - forward)
            td_backward = abs(appt_datetime - backward)
            if td_forward <= td_backward:
                appt_datetime = forward
            else:
                appt_datetime = backward
            if not appt_datetime:
                raise TypeError('Appt_datetime cannot be None')
        return appt_datetime

    def move_on_appt_max_exceeded(self, original_appt_datetime, site, appointments_per_day_max=None,
                                  appointments_days_formard=None):
        """Moves edc_appointment date to another date if the appointments_per_day_max is exceeded."""
        appt_datetime = copy.deepcopy(original_appt_datetime)
        if not appointments_per_day_max:
            appointments_per_day_max = self.appointments_per_day_max
        if not appointments_days_formard:
            appointments_days_formard = self.appointments_days_formard
        my_appt_date = appt_datetime.date()
        # get a list of appointments in the date range from 'appt_datetime' to 'appt_datetime'+days_forward
        # use model field edc_appointment.best_appt_datetime not edc_appointment.appt_datetime
        # TODO: change this query to allow the search to go to the beginning of the week
        Appointment = django_apps.get_model('edc_appointment', 'edc_appointment')
        appointments = Appointment.objects.filter(
            study_site=site,
            best_appt_datetime__gte=appt_datetime,
            best_appt_datetime__lte=appt_datetime + timedelta(days=self.appointments_days_formard))
        if appointments:
            # looking for appointments per day
            # create dictionary of { day: count, ... }
            appt_dates = [appointment.appt_datetime.date() for appointment in appointments]
            appt_date_counts = dict((i, appt_dates.count(i)) for i in appt_dates)
            # if desired date is not maxed out, use it
            if appt_date_counts.get(my_appt_date) < appointments_per_day_max:
                appt_date = my_appt_date
            else:
                # look for an alternative date
                for appt_date, cnt in dict((i, appt_dates.count(i)) for i in appt_dates).items():
                    # only looking forward at the moment unless Appointments query is changed above
                    if cnt < appointments_per_day_max and appt_date > my_appt_date:
                        self.message = 'Appointment date has been moved to {0}.'.format(appt_date)
                        break
            # return an edc_appointment datetime that uses the time from the originally desrired datetime
            appt_datetime = datetime(
                appt_date.year, appt_date.month, appt_date.day, appt_datetime.hour, appt_datetime.minute)
        if not appt_datetime:
            raise TypeError('Appt_datetime cannot be None')
        return appt_datetime

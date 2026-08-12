import calendar
from datetime import datetime, date, timedelta
from django.utils.timezone import make_aware, get_current_timezone
from bookings.models import AvailabilityBlock
from catalog.models import VehicleMaintenance


def _sold_out_coverage(intervals, window_start, window_end, quantity):
    """Return (has_sold_out_time, sold_out_for_whole_window)."""
    events = []
    for start_at, end_at in intervals:
        clipped_start = max(start_at, window_start)
        clipped_end = min(end_at, window_end)
        if clipped_start >= clipped_end:
            continue
        events.append((clipped_start, 1))
        events.append((clipped_end, -1))

    if not events:
        return False, False

    # End events are processed before start events at the same instant so
    # back-to-back rentals do not temporarily consume two units.
    events.sort(key=lambda item: (item[0], item[1]))
    occupied = 0
    cursor = window_start
    sold_out_duration = timedelta(0)
    for event_at, delta in events:
        if event_at > cursor and occupied >= quantity:
            sold_out_duration += event_at - cursor
        occupied += delta
        cursor = event_at
    if cursor < window_end and occupied >= quantity:
        sold_out_duration += window_end - cursor

    window_duration = window_end - window_start
    return sold_out_duration > timedelta(0), sold_out_duration >= window_duration

def get_vehicle_availability_calendar(vehicle, year, month):
    tz = get_current_timezone()
    _, num_days = calendar.monthrange(year, month)
    
    first_day = make_aware(datetime(year, month, 1), tz)
    next_month = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    last_day = make_aware(datetime.combine(next_month, datetime.min.time()), tz)
    
    # Fetch all potentially overlapping events
    # We query blocks, bookings, and maintenance
    blocks = AvailabilityBlock.objects.filter(
        vehicle=vehicle,
        start_at__lt=last_day,
        end_at__gt=first_day
    )
    maintenance_records = VehicleMaintenance.objects.filter(
        vehicle=vehicle,
        start_at__lt=last_day,
        end_at__gt=first_day,
        status__in=['scheduled', 'in_progress'],
    )
    
    days_data = []
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        day_start = make_aware(datetime.combine(current_date, datetime.min.time()), tz)
        day_end = day_start + timedelta(days=1)
        
        day_blocks = [b for b in blocks if b.start_at < day_end and b.end_at > day_start]
        
        status = "available"
        slots = []
        
        # Check for maintenance or manual blocks first
        maintenance_blocks = [b for b in day_blocks if b.type in ['maintenance', 'manual_block']]
        booking_blocks = [b for b in day_blocks if b.type == 'booking']
        day_maintenance_records = [
            record
            for record in maintenance_records
            if record.start_at < day_end and record.end_at > day_start
        ]

        quantity = vehicle.quantity or 1
        all_intervals = [
            (block.start_at, block.end_at)
            for block in maintenance_blocks + booking_blocks
        ] + [
            (record.start_at, record.end_at)
            for record in day_maintenance_records
        ]
        has_sold_out_time, sold_out_all_day = _sold_out_coverage(
            all_intervals,
            day_start,
            day_end,
            quantity,
        )

        if has_sold_out_time and (maintenance_blocks or day_maintenance_records) and not booking_blocks:
            status = "maintenance"
        elif sold_out_all_day:
            status = "maintenance" if (maintenance_blocks or day_maintenance_records) else "booked"
        elif has_sold_out_time:
            status = "partially_booked"

        for b in booking_blocks:
            slots.append({
                "start": b.start_at.isoformat(),
                "end": b.end_at.isoformat(),
                "type": "booking"
            })
        
        days_data.append({
            "date": current_date.isoformat(),
            "status": status,
            "slots": slots
        })
        
    return {
        "scooter_id": vehicle.id,
        "year": year,
        "month": month,
        "days": days_data
    }

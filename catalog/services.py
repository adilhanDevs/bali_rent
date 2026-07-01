import calendar
from datetime import datetime, date, timedelta
from django.utils.timezone import make_aware, get_current_timezone
from django.db.models import Q
from bookings.models import AvailabilityBlock, Booking
from catalog.models import VehicleMaintenance

def get_vehicle_availability_calendar(vehicle, year, month):
    tz = get_current_timezone()
    _, num_days = calendar.monthrange(year, month)
    
    first_day = make_aware(datetime(year, month, 1), tz)
    last_day = make_aware(datetime(year, month, num_days, 23, 59, 59), tz)
    
    # Fetch all potentially overlapping events
    # We query blocks, bookings, and maintenance
    blocks = AvailabilityBlock.objects.filter(
        vehicle=vehicle,
        start_at__lt=last_day,
        end_at__gt=first_day
    )
    
    # We could also query Bookings directly if blocks are not synced yet
    # But let's assume blocks are the source of truth for the calendar
    # or we query them all and merge.
    
    days_data = []
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        day_start = make_aware(datetime.combine(current_date, datetime.min.time()), tz)
        day_end = make_aware(datetime.combine(current_date, datetime.max.time()), tz)
        
        day_blocks = [b for b in blocks if b.start_at < day_end and b.end_at > day_start]
        
        status = "available"
        slots = []
        
        # Check for maintenance or manual blocks first
        maintenance_blocks = [b for b in day_blocks if b.type in ['maintenance', 'manual_block']]
        booking_blocks = [b for b in day_blocks if b.type == 'booking']
        
        quantity = vehicle.quantity or 1
        # Maintenance/manual blocks each take one physical unit out of service for the day.
        units_after_maintenance = quantity - len(maintenance_blocks)

        if units_after_maintenance <= 0:
            status = "maintenance"
        elif booking_blocks:
            # A day is only "booked" once every remaining unit is taken for the whole day.
            # We count bookings that cover the entire day and compare against remaining units.
            full_day_bookings = sum(
                1 for b in booking_blocks if b.start_at <= day_start and b.end_at >= day_end
            )

            if full_day_bookings >= units_after_maintenance:
                status = "booked"
            else:
                status = "partially_booked"
            
            # Add slots info
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

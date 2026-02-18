import { useState, useEffect } from 'react';
import DatePicker, { DateObject } from 'react-multi-date-picker';
import persian from 'react-date-object/calendars/persian';
import persian_fa from 'react-date-object/locales/persian_fa';
import { CalendarDays } from 'lucide-react';
import { cn } from '@/lib/utils';

interface JalaliDatePickerProps {
  value?: string; // Gregorian date string (YYYY-MM-DD)
  onChange: (date: string) => void;
  minDate?: string; // Gregorian date string (YYYY-MM-DD)
  placeholder?: string;
  hasError?: boolean;
  className?: string;
}

export function JalaliDatePicker({
  value,
  onChange,
  minDate,
  placeholder = 'انتخاب تاریخ',
  hasError = false,
  className,
}: JalaliDatePickerProps) {
  const [dateValue, setDateValue] = useState<DateObject | null>(null);
  const [minDateObject, setMinDateObject] = useState<DateObject | null>(null);

  // Convert Gregorian string to DateObject
  useEffect(() => {
    if (value) {
      const [year, month, day] = value.split('-').map(Number);
      const dateObj = new DateObject({ year, month, day, calendar: persian });
      setDateValue(dateObj);
    } else {
      setDateValue(null);
    }
  }, [value]);

  // Convert minDate to DateObject
  useEffect(() => {
    if (minDate) {
      const [year, month, day] = minDate.split('-').map(Number);
      const dateObj = new DateObject({ year, month, day, calendar: persian });
      setMinDateObject(dateObj);
    }
  }, [minDate]);

  const handleChange = (date: DateObject | null) => {
    if (date) {
      // Convert Persian date to Gregorian for storage
      const gregorian = date.convert(undefined, undefined);
      const year = gregorian.year;
      const month = String(gregorian.month.number).padStart(2, '0');
      const day = String(gregorian.day).padStart(2, '0');
      onChange(`${year}-${month}-${day}`);
    }
  };

  return (
    <div className={cn('relative w-full', className)}>
      <DatePicker
        value={dateValue}
        onChange={handleChange}
        calendar={persian}
        locale={persian_fa}
        minDate={minDateObject}
        calendarPosition="bottom-right"
        containerClassName="w-full"
        inputClass={cn(
          'w-full h-11 px-4 pr-11 rounded-lg border bg-background text-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer',
          'placeholder:text-muted-foreground',
          hasError ? 'border-destructive' : 'border-input'
        )}
        placeholder={placeholder}
        format="DD MMMM YYYY"
        arrow={false}
        mapDays={({ date, isSameDate }) => {
          const isToday = isSameDate(date, new DateObject({ calendar: persian }));
          return {
            className: isToday ? 'today-highlight' : '',
          };
        }}
        className="jalali-datepicker"
        render={(value, openCalendar) => (
          <button
            type="button"
            onClick={openCalendar}
            className={cn(
              'w-full h-11 px-4 rounded-lg border bg-background text-foreground text-right',
              'focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer flex items-center justify-between',
              hasError ? 'border-destructive' : 'border-input',
              !value && 'text-muted-foreground'
            )}
          >
            <CalendarDays className="w-5 h-5 text-muted-foreground" />
            <span>{value || placeholder}</span>
          </button>
        )}
      />
      <style>{`
        .jalali-datepicker {
          width: 100%;
          font-family: inherit;
        }
        .rmdp-container {
          width: 100%;
        }
        .rmdp-wrapper {
          border-radius: 1rem;
          box-shadow: 0 10px 40px -10px hsl(var(--primary) / 0.2);
          border: 1px solid hsl(var(--border));
          background: hsl(var(--card));
        }
        .rmdp-calendar {
          padding: 1rem;
          background: transparent;
        }
        .rmdp-header {
          padding: 0.5rem 0;
          margin-bottom: 0.5rem;
        }
        .rmdp-header-values {
          font-weight: 600;
          color: hsl(var(--foreground));
          font-size: 1rem;
        }
        .rmdp-arrow-container {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 2rem;
          height: 2rem;
          border-radius: 0.5rem;
          background: hsl(var(--accent));
          transition: all 0.2s;
        }
        .rmdp-arrow-container:hover {
          background: hsl(var(--primary));
        }
        .rmdp-arrow-container:hover .rmdp-arrow {
          border-color: hsl(var(--primary-foreground));
        }
        .rmdp-arrow {
          border: solid hsl(var(--foreground));
          border-width: 0 2px 2px 0;
          width: 7px;
          height: 7px;
        }
        .rmdp-week-day {
          color: hsl(var(--muted-foreground));
          font-size: 0.75rem;
          font-weight: 500;
          padding: 0.5rem 0;
        }
        .rmdp-day {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 0.75rem;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
          color: hsl(var(--foreground));
          font-weight: 500;
        }
        .rmdp-day span {
          font-size: 0.875rem;
        }
        .rmdp-day:not(.rmdp-disabled):not(.rmdp-deactive):hover {
          background: hsl(var(--accent));
          color: hsl(var(--accent-foreground));
        }
        .rmdp-day.rmdp-today span {
          background: hsl(var(--primary) / 0.1);
          color: hsl(var(--primary));
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 0.75rem;
        }
        .rmdp-day.rmdp-selected span:not(.highlight) {
          background: hsl(var(--primary));
          color: hsl(var(--primary-foreground));
          box-shadow: 0 4px 12px hsl(var(--primary) / 0.4);
        }
        .rmdp-day.rmdp-disabled,
        .rmdp-day.rmdp-disabled:hover {
          color: hsl(var(--muted-foreground));
          opacity: 0.4;
          cursor: not-allowed;
        }
        .rmdp-day.rmdp-deactive {
          color: hsl(var(--muted-foreground));
          opacity: 0.4;
        }
        .rmdp-shadow {
          box-shadow: none;
        }
        .today-highlight span {
          font-weight: 700 !important;
        }
      `}</style>
    </div>
  );
}

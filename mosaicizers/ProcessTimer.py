from datetime import datetime


class ProcessTimer:
    def __init__(self, process_name, start_time=None):
        self.process_name = process_name
        # slight non-standard to make sure "now" is when
        # init is invoked.
        self.start_time = start_time if start_time else datetime.now()

        print(f"[{self.process_name}] Process started at: \
            {self.start_time.strftime('%Y %b %d %H:%M:%S')}")

    def finish(self):
        end_time = datetime.now()
        print(f"[{self.process_name}] Process ended at: \
            {end_time.strftime('%Y %b %d %H:%M:%S')}")

        # Calculate duration
        duration = end_time - self.start_time
        total_seconds = int(duration.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        total_minutes = total_seconds // 60

        print(f"Total time was: {hours} hours {minutes} \
              minutes {seconds} seconds \
              ({total_minutes} total minutes)")

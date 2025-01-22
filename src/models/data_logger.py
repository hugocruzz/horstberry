from pathlib import Path
from datetime import datetime
import csv

class DataLogger:
    def __init__(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.filepath = log_dir / f"flow_data_{timestamp}.csv"
        
        with open(self.filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Flow1_SP', 'Flow1_PV', 'Flow2_SP', 'Flow2_PV'])

    def log_data(self, data: dict):
        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                data['flow1_sp'],
                data['flow1_pv'],
                data['flow2_sp'],
                data['flow2_pv']
            ])
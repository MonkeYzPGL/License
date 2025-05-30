'''
Analiza datelor (Data Analysis)
Citirea datelor din fisiere pentru casa 3 din fisierele .dat.
Vizualizarea datelor sub forma de grafice pentru fiecare din canale.
Analizarea distributiei pentru fiecare aparat.
'''

import os
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from tabulate import tabulate
import re

class DataAnalyzer:
    def __init__(self, house_dir, labels_file, channels):
        self.house_dir = house_dir
        self.labels_file = labels_file
        self.channels = channels
        self.labels = {}
        self.data_dict = {}
        self.metrics_df = None

    def load_labels(self):
        """Incarcare labels din fisier."""
        try:
            with open(self.labels_file, 'r') as f:
                channels_dict = {}

                for line in f:
                    if line.strip():
                        channel, label = line.strip().split(' ', 1)
                        channel_num = int(re.search(r'\d+', channel).group())  # Extrage numărul canalului
                        channels_dict[channel_num] = (channel, label)  # Stochează în dicționar

                #  Sortează canalele numeric
                sorted_labels = dict(sorted(channels_dict.items()))

                #  Reconvertim dicționarul în formatul inițial
                for channel_num, (channel, label) in sorted_labels.items():
                    self.labels[f"channel_{channel}.dat"] = label

            print("Labels loaded successfully.")
        except Exception as e:
            print(f"Error loading labels: {e}")

    def load_channel_data(self, file_path):
        """Incarcare timeseries din fisier."""
        try:
            data = pd.read_csv(file_path, delimiter=' ', names=['timestamp', 'power'], header=None)
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
            data.set_index('timestamp', inplace=True)
            return data
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def load_data(self):
        """Incarcare data din fisier pentru fiecare canal."""
        self.channels.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))


        for channel in self.channels:
            file_path = os.path.join(self.house_dir, channel)
            if os.path.exists(file_path):
                print(f"Loading {channel}...")
                self.data_dict[channel] = self.load_channel_data(file_path)
            else:
                print(f"File not found: {file_path}")

    def plot_time_series(self):
        """Plot time series pentru fiecare canal."""
        for channel, data in self.data_dict.items():
            if data is not None:
                plt.figure(figsize=(12, 6))
                plt.plot(data.index, data['power'], label=f"{self.labels.get(channel, 'Unknown')} (Power)")
                plt.xlabel("Time")
                plt.ylabel("Power (W)")
                plt.title(f"Time Series of {self.labels.get(channel, 'Unknown')}")
                plt.legend()
                plt.show()

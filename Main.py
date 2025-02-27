from Analysis.DataAnalysis import DataAnalyzer
from Metrics.Metrics import MetricsAnalyzer
from Analysis.AggregationAnalysis import AggregationAnalyzer
from LSTM_Model.LSTMAnalysis import LSTMAnalyzer
from Metrics.ErrorMetrics import ErrorMetricsAnalyzer
import os
import pandas as pd

if __name__ == "__main__":
    # Definim directoarele principale
    base_dir = r'C:\Users\elecf\Desktop\Licenta\Date\UK-DALE-disaggregated\house_3'
    labels_file = os.path.join(base_dir, 'labels.dat')
    channels = ['channel_1.dat', 'channel_2.dat', 'channel_3.dat', 'channel_4.dat', 'channel_5.dat']

    # Cream sub-directoarele pentru organizarea fisierelor
    aggregated_dir = os.path.join(base_dir, "aggregated")
    downsampled_dir = os.path.join(base_dir, "downsampled")
    metrics_dir = os.path.join(base_dir, "metrics")
    predictii_dir = os.path.join(base_dir, "predictii")

    os.makedirs(aggregated_dir, exist_ok=True)
    os.makedirs(downsampled_dir, exist_ok=True)
    os.makedirs(metrics_dir, exist_ok=True)
    os.makedirs(predictii_dir, exist_ok=True)

    # Initializam DataAnalyzer
    analyzer = DataAnalyzer(house_dir=base_dir, labels_file=labels_file, channels=channels)

    # Incarcam etichetele si datele
    analyzer.load_labels()
    analyzer.load_data()

    # Vizualizam datele pentru fiecare canal
    #analyzer.plot_time_series()

    # Calculam si afisam metricile generale pentru fiecare canal
    metrics_analyzer = MetricsAnalyzer(data_dict=analyzer.data_dict, labels=analyzer.labels)

    # Salvam metricile generale in `metrics/`
    general_metrics_path = os.path.join(metrics_dir, "general_metrics.csv")
    daily_avg = metrics_analyzer.calculate_daily_average()
    peaks = metrics_analyzer.identify_peaks()
    correlation = metrics_analyzer.calculate_correlation()

    metrics_analyzer.metrics_df = {
        'Daily Averages': daily_avg,
        'Peaks': peaks,
        'Correlations': correlation
    }
    metrics_analyzer.save_metrics(output_path=general_metrics_path)

    # Initializam PlotAnalyzer pentru vizualizari suplimentare
    #plot_analyzer = PlotAnalyzer(data_dict=analyzer.data_dict, labels=analyzer.labels)

    #plot_analzyzer.plot_histograms()  # Histogramele pentru distributia consumului
    #plot_analyzer.plot_correlograms()  # Corelograme pentru analiza corelatiilor

    # Analizam agregarea datelor
    aggregation_analyzer = AggregationAnalyzer(data_dict=analyzer.data_dict, labels=analyzer.labels)

    # Salvam datele agregate si cele cu granularitate redusa in directoarele respective
    aggregation_analyzer.save_aggregated_data(freq='D', output_dir=aggregated_dir)
    aggregation_analyzer.save_downsampled_data(freq='1T', output_dir=downsampled_dir)

    # Verificam daca exista fisierul cu datele downsampled pentru canalul 5
    channel_5_downsampled_path = os.path.join(downsampled_dir, 'channel_4.dat_downsampled_10S.csv')

    if os.path.exists(channel_5_downsampled_path):
        print(f"✅ File found: {channel_5_downsampled_path}")

        # Initializam si rulam modelul LSTM
        lstm_analyzer = LSTMAnalyzer(csv_path=channel_5_downsampled_path)
        lstm_analyzer.preprocess_data()

        # Antrenare model
        lstm_analyzer.train()

        # Generam predictii
        predictions, actuals = lstm_analyzer.predict()

        # Salvam predictiile in folderul `predictii/`
        prediction_output_path = os.path.join(predictii_dir, 'channel_4_predictions.csv')
        prediction_df = pd.DataFrame({'Predictions': predictions, 'Actuals': actuals})
        prediction_df.to_csv(prediction_output_path, index=False)
        print(f"✅ Predictions saved in: {prediction_output_path}")

        # Calculam si salvam metricile de eroare in `metrics/`
        error_metrics_path = os.path.join(metrics_dir, "channel_4_lstm_error_metrics.csv")
        error_metrics_analyzer = ErrorMetricsAnalyzer(predictions=predictions, actuals=actuals, output_path=error_metrics_path)
        error_metrics_analyzer.save_metrics()
        print(f"✅ Error metrics saved in: {error_metrics_path}")

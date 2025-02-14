import torch
from torch.utils.data import DataLoader, Dataset
import pandas as pd
import matplotlib.pyplot as plt
from LSTM_Model.LSTM import LSTMModel
import torch.nn as nn
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import torch.optim.lr_scheduler as lr_scheduler
import time

class TimeSeriesDataset(Dataset):
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

class LSTMAnalyzer:
    def __init__(self, csv_path, window_size=20, batch_size=512, hidden_size=256, learning_rate=0.001, device=None):
        self.csv_path = csv_path
        self.window_size = window_size
        self.batch_size = batch_size
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Utlizare dispozivitivul : {torch.cuda.get_device_name(0)}")

        # Modelul LSTM
        self.model = LSTMModel(input_size=6, hidden_size=hidden_size, output_size=1).to(self.device)

        # Functia de cost si optimizer si scheduler-ul pentru Learning Rate
        self.criterion = nn.SmoothL1Loss() #MAE
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        self.scheduler = lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='min', factor=0.5, patience=3, verbose=True)

    # Adăugăm print-uri pentru a măsura timpul fiecărei operațiuni din preprocess_data
    def preprocess_data(self):
        """Incarca si preproceseaza datele."""
        data = pd.read_csv(self.csv_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data['day_of_week'] = data['timestamp'].dt.dayofweek
        data['hour_of_day'] = data['timestamp'].dt.hour
        data['power'] = pd.to_numeric(data['power'], errors='coerce').fillna(0)

        lags = [12, 24, 48]
        for lag in lags:
            data[f'lag_{lag}h'] = data['power'].shift(lag)
        data.fillna(0, inplace=True)

        data['rolling_mean_12h'] = data['power'].rolling(window=12, min_periods=1).mean()

        self.scaler = MinMaxScaler(feature_range=(0, 1))

        scaled_features = self.scaler.fit_transform(data[['power', 'day_of_week', 'hour_of_day', 'lag_12h', 'lag_24h', 'lag_48h']])
        data[['scaled_power', 'scaled_day_of_week', 'scaled_hour_of_day', 'scaled_lag_12h', 'scaled_lag_24h', 'scaled_lag_48h']] = scaled_features
        selected_features = ['scaled_power', 'scaled_day_of_week', 'scaled_hour_of_day', 'scaled_lag_12h', 'scaled_lag_24h', 'scaled_lag_48h']
        X, y = self.create_sequences(data[selected_features].values)

        # Impartirea datelor in antrenare/validare/test
        train_size = int(0.8 * len(X))
        val_size = int(0.1 * len(X))

        X_train, y_train = X[:train_size], y[:train_size]
        X_val, y_val = X[train_size:train_size + val_size], y[train_size:train_size + val_size]
        X_test, y_test = X[train_size + val_size:], y[train_size + val_size:]

        # Cream DataLoaders
        self.train_loader = DataLoader(TimeSeriesDataset(X_train, y_train), batch_size=self.batch_size, shuffle=True)
        self.val_loader = DataLoader(TimeSeriesDataset(X_val, y_val), batch_size=self.batch_size, shuffle=False)
        self.test_loader = DataLoader(TimeSeriesDataset(X_test, y_test), batch_size=self.batch_size, shuffle=False)

    def create_sequences(self, data):

        sequences = [data[i:i + self.window_size] for i in range(len(data) - self.window_size)]
        labels = [data[i + self.window_size, 0] for i in range(len(data) - self.window_size)]
        return torch.tensor(np.array(sequences), dtype=torch.float32), torch.tensor(np.array(labels), dtype=torch.float32)

    def train(self, epochs=100, patience=5):
        """Antreneaza modelul LSTM , folosind si Early Stopping."""
        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        patience_counter = 0

        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0

            for X_batch, y_batch in self.train_loader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                self.optimizer.zero_grad()
                y_pred = self.model(X_batch)
                loss = self.criterion(y_pred.squeeze(), y_batch)
                loss.backward()
                self.optimizer.step()
                train_loss += loss.item()

            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for X_batch, y_batch in self.val_loader:
                    X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                    y_pred = self.model(X_batch)
                    val_loss += self.criterion(y_pred.squeeze(), y_batch).item()

            train_losses.append(train_loss / len(self.train_loader))
            val_losses.append(val_loss / len(self.val_loader))

            print(f"Epoch {epoch + 1}/{epochs}, Train Loss: {train_losses[-1]:.4f}, Val Loss: {val_losses[-1]:.4f}")

            if epoch > 8:
                for param_group in self.optimizer.param_groups:
                    param_group["lr"] *= 0.9  # 🔹 Reducem LR cu 50%
                    print(f"🔽 Learning Rate redus la {param_group['lr']:.6f}")

            # EARLY STOPPING: verificam daca loss-ul pe validare nu mai scade
            if val_losses[-1] < best_val_loss:
                best_val_loss = val_losses[-1]
                patience_counter = 0  # Resetare counter daca loss-ul scade
            else:
                patience_counter += 1  # Resetare counter daca loss-ul NU scade

            if patience_counter >= patience:
                print(f"🔴 Early stopping activat! Antrenarea se opreste la epoch {epoch + 1}.")
                break  # Iesire din train loop
            self.scheduler.step(val_losses[-1])

        # Plot Train vs Validation Loss
        plt.plot(train_losses, label="Train Loss")
        plt.plot(val_losses, label="Validation Loss")
        plt.legend()
        plt.title("Train vs Validation Loss")
        plt.show()

    def predict(self):
        """Genereaza predictii si denormalizeaza rezultatele."""
        self.model.eval()
        predictions, actuals = [], []
        with torch.no_grad():
            for X_batch, y_batch in self.test_loader:
                X_batch = X_batch.to(self.device)
                y_pred = self.model(X_batch).squeeze().cpu().numpy()

                # Aplicăm regula: Dacă valoarea reală este 0, forțăm predicția să fie 0
                y_pred = np.where(y_batch.cpu().numpy() == 0, 0, y_pred)

                # Denormalizare
                y_pred_expanded = np.zeros((len(y_pred), 6))  # 6 este numarul de features
                y_pred_expanded[:, 0] = y_pred
                y_pred = self.scaler.inverse_transform(y_pred_expanded)[:, 0]
                y_pred = np.maximum(0, y_pred)

                y_batch_expanded = np.zeros((len(y_batch.cpu().numpy()), 6))
                y_batch_expanded[:, 0] = y_batch.cpu().numpy()
                y_batch = self.scaler.inverse_transform(y_batch_expanded)[:, 0]

                predictions.extend(y_pred)
                actuals.extend(y_batch)

        return predictions, actuals
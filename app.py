from flask import Flask, jsonify, request
from fundamentus import get_resultado
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Parâmetros de filtro padrão
DEFAULT_FILTERS = {
    "pl": (0, 15),
    "pvp": (0, 1),
    "dy": (0.04, 100),
    "mrgliq": (0.10, 10),
    "roe": (0.10, 100),
    "divbpatr": (0, 1)
}

@app.route('/empresas_perenes', methods=['POST'])
def get_perennial_companies():
    # Recebe filtros personalizados do front-end
    filters = request.json.get('filters', DEFAULT_FILTERS)

    # Obter dados do Fundamentus
    resultado = get_resultado()
    # print(resultado)

    # Converter valores para numéricos, forçando erros para NaN
    for column in resultado.columns:
        resultado[column] = pd.to_numeric(resultado[column], errors='coerce')

    # Aplicar filtros
    for key, (min_val, max_val) in filters.items():
        resultado = resultado[(resultado[key] >= min_val) & (resultado[key] <= max_val)]

    # Resetar o índice
    resultado.reset_index(inplace=True)

    # Obter os tickers das empresas filtradas
    tickers = resultado['papel'].tolist()
    print(tickers)
    return jsonify(tickers)

@app.route('/backtest', methods=['POST'])
def backtest():
    tickers = request.json.get('tickers', [])
    periods = request.json.get('periods', {"1y": 1, "5y": 5, "10y": 10})

    ibov = "^BVSP"
    results = {}
    end_date = datetime.now()

    for label, years in periods.items():
        start_date = end_date - timedelta(days=365 * years)
        
        # Obter dados históricos do Ibovespa
        ibov_data = yf.download(ibov, start=start_date, end=end_date)['Adj Close']
        ibov_cumulative_return = (ibov_data / ibov_data.iloc[0]) * 100  # Rentabilidade acumulada do Ibov

        # Criar DataFrame para os retornos acumulados dos tickers
        cumulative_returns = pd.DataFrame()

        for ticker in tickers:
            ticker_data = yf.download(ticker + ".SA", start=start_date, end=end_date)['Adj Close']
            if len(ticker_data) > 0:
                cumulative_return = (ticker_data / ticker_data.iloc[0]) * 100  # Rentabilidade acumulada
                cumulative_returns[ticker] = cumulative_return

        # Calcular a média dos retornos acumulados dos tickers
        average_cumulative_return = cumulative_returns.mean(axis=1)

        results[label] = {
            "average_return": average_cumulative_return.iloc[-1],
            "ibov_return": ibov_cumulative_return.iloc[-1]
        }
        
        # Plotar os resultados
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')
        plt.plot(average_cumulative_return, label="Average Return", color='green')
        plt.plot(ibov_cumulative_return, label="Ibovespa Return", color='blue')
        plt.title(f"Backtest - {label}", color='white')
        plt.ylabel("Cumulative Return (%)", color='white')
        plt.xlabel("Date", color='white')
        plt.legend(facecolor='black', edgecolor='white', labelcolor='white')
        plt.grid(True, color='gray', linestyle='--')
        plt.tick_params(axis='x', colors='white')
        plt.tick_params(axis='y', colors='white')

        # Salvar o gráfico em uma string base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()

        results[label]['chart'] = image_base64

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)

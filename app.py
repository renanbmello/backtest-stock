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
CORS(app)

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
        
        # Obter dados históricos
        ibov_data = yf.download(ibov, start=start_date, end=end_date)['Adj Close']
        returns_ibov = (ibov_data[-1] / ibov_data[0] - 1) * 100

        returns_tickers = []
        for ticker in tickers:
            ticker_data = yf.download(ticker + ".SA", start=start_date, end=end_date)['Adj Close']
            if len(ticker_data) > 0:
                returns_ticker = (ticker_data[-1] / ticker_data[0] - 1) * 100
                returns_tickers.append(returns_ticker)

        average_return = sum(returns_tickers) / len(returns_tickers) if returns_tickers else 0

        results[label] = {
            "average_return": average_return,
            "ibov_return": returns_ibov
        }
        
        # Plotar os resultados
        plt.figure(figsize=(10, 6))
        labels = ['Average Return', 'Ibovespa Return']
        returns = [average_return, returns_ibov]
        plt.bar(labels, returns, color=['blue', 'green'])
        plt.title(f"Backtest - {label}")
        plt.ylabel("Return (%)")
        plt.grid(True)

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

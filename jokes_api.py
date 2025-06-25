from flask import Flask, request, jsonify
import pickle
import json
import os
from datetime import datetime
from collections import defaultdict, deque
import pandas as pd

app = Flask("jokes_recommendation_api")

# Archivo para guardar las clasificaciones de usuarios
RATINGS_FILE = "user_ratings.json"

# Cargar el modelo entrenado
try:
    with open("svd_model2.pkl", "rb") as f:
        model = pickle.load(f)
    print("✅ Modelo SVD cargado exitosamente desde svd_model.pkl")
except FileNotFoundError:
    try:
        with open("svd_model2.pkl", "rb") as f:
            model = pickle.load(f)
        print("✅ Modelo SVD cargado exitosamente desde svd_model2.pkl")
    except FileNotFoundError:
        print("❌ Error: No se encontró ningún archivo de modelo (svd_model.pkl o svd_model2.pkl)")
        model = None

# Cargar datos de chistes
try:
    jokes_df = pd.read_csv("jokes.csv")
    print(f"✅ Dataset de chistes cargado: {len(jokes_df)} chistes disponibles")
except FileNotFoundError:
    print("❌ Error: No se encontró el archivo jokes.csv")
    jokes_df = None

# Estructura para guardar las últimas 3 clasificaciones por usuario
# Formato: {user_id: deque([(joke_id, rating, timestamp), ...], maxlen=3)}
user_ratings = defaultdict(lambda: deque(maxlen=3))

def load_user_ratings():
    """Cargar las clasificaciones guardadas desde archivo"""
    global user_ratings
    if os.path.exists(RATINGS_FILE):
        try:
            with open(RATINGS_FILE, 'r') as f:
                data = json.load(f)
                for user_id, ratings_list in data.items():
                    user_ratings[int(user_id)] = deque(
                        [(r['joke_id'], r['rating'], r['timestamp']) for r in ratings_list],
                        maxlen=3
                    )
            print(f"✅ Clasificaciones de usuarios cargadas desde {RATINGS_FILE}")
        except Exception as e:
            print(f"⚠️ Error cargando clasificaciones: {e}")

def save_user_ratings():
    """Guardar las clasificaciones actuales en archivo"""
    try:
        data = {}
        for user_id, ratings_deque in user_ratings.items():
            data[str(user_id)] = [
                {
                    'joke_id': joke_id,
                    'rating': rating,
                    'timestamp': timestamp
                }
                for joke_id, rating, timestamp in ratings_deque
            ]
        
        with open(RATINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Clasificaciones guardadas en {RATINGS_FILE}")
    except Exception as e:
        print(f"❌ Error guardando clasificaciones: {e}")

def get_user_preference_bias(user_id):
    """Calcular el sesgo de preferencia del usuario basado en sus últimas clasificaciones"""
    if user_id not in user_ratings or len(user_ratings[user_id]) == 0:
        return 0.0  # Sin sesgo para usuarios nuevos
    
    ratings = [rating for _, rating, _ in user_ratings[user_id]]
    avg_rating = sum(ratings) / len(ratings)
    
    # Convertir a escala -10 a 10 (asumiendo que la app envía 0-10)
    # Si el usuario tiende a dar ratings altos, sesgo positivo
    # Si tiende a dar ratings bajos, sesgo negativo
    bias = (avg_rating - 5.0) * 2  # Escalar de 0-10 a -10,10
    return bias

# Cargar clasificaciones al iniciar
load_user_ratings()

@app.route("/", methods=["GET"])
def hello_world():
    return jsonify({
        "message": "🎭 API de Recomendación de Chistes",
        "status": "activa",
        "endpoints": {
            "/predict/jokes": "GET - Predecir rating de un chiste",
            "/rate/joke": "POST - Clasificar un chiste",
            "/recommend/jokes": "GET - Obtener mejores chistes para usuario",
            "/user/ratings": "GET - Ver últimas clasificaciones del usuario"
        }
    })

@app.route("/predict/jokes", methods=["GET"])
def predict_joke():
    """Predecir el rating de un chiste específico para un usuario"""
    try:
        user_id = int(request.args.get("user_id"))
        joke_id = int(request.args.get("joke_id"))
        
        if model is None:
            return jsonify({"error": "Modelo no disponible"}), 500
        
        # Predicción base del modelo
        pred = model.predict(user_id, joke_id)
        base_rating = pred.est
        
        # Aplicar sesgo de preferencia del usuario
        user_bias = get_user_preference_bias(user_id)
        adjusted_rating = base_rating + (user_bias * 0.3)  # Factor de ajuste
        
        # Mantener en rango válido
        adjusted_rating = max(-10, min(10, adjusted_rating))
        
        return jsonify({
            "user_id": user_id,
            "joke_id": joke_id,
            "predicted_rating": round(adjusted_rating, 3),
            "base_prediction": round(base_rating, 3),
            "user_bias": round(user_bias, 3),
            "user_ratings_count": len(user_ratings.get(user_id, []))
        })
        
    except ValueError:
        return jsonify({"error": "user_id y joke_id deben ser números enteros"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rate/joke", methods=["POST"])
def rate_joke():
    """Guardar la clasificación de un usuario para un chiste"""
    try:
        data = request.get_json()
        user_id = int(data.get("user_id"))
        joke_id = int(data.get("joke_id"))
        rating = float(data.get("rating"))
        
        # Validar rating en escala 0-10
        if not (0 <= rating <= 10):
            return jsonify({"error": "Rating debe estar entre 0 y 10"}), 400
        
        # Guardar la clasificación con timestamp
        timestamp = datetime.now().isoformat()
        user_ratings[user_id].append((joke_id, rating, timestamp))
        
        # Guardar en archivo
        save_user_ratings()
        
        return jsonify({
            "message": "Clasificación guardada exitosamente",
            "user_id": user_id,
            "joke_id": joke_id,
            "rating": rating,
            "total_ratings": len(user_ratings[user_id]),
            "timestamp": timestamp
        })
        
    except (ValueError, TypeError):
        return jsonify({"error": "Datos inválidos. Se requiere user_id (int), joke_id (int), rating (float)"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/recommend/jokes", methods=["GET"])
def recommend_jokes():
    """Recomendar los mejores chistes para un usuario"""
    try:
        user_id = int(request.args.get("user_id"))
        top_n = int(request.args.get("top_n", 5))  # Por defecto 5 recomendaciones
        
        if model is None or jokes_df is None:
            return jsonify({"error": "Modelo o datos de chistes no disponibles"}), 500
        
        # Obtener todos los joke_ids disponibles
        all_joke_ids = jokes_df['joke_id'].tolist()
        
        # Predecir ratings para todos los chistes
        predictions = []
        user_bias = get_user_preference_bias(user_id)
        
        for joke_id in all_joke_ids:
            try:
                pred = model.predict(user_id, joke_id)
                base_rating = pred.est
                adjusted_rating = base_rating + (user_bias * 0.3)
                adjusted_rating = max(-10, min(10, adjusted_rating))
                
                # Obtener el texto del chiste
                joke_text = jokes_df[jokes_df['joke_id'] == joke_id]['joke_text'].iloc[0]
                
                predictions.append({
                    'joke_id': joke_id,
                    'predicted_rating': round(adjusted_rating, 3),
                    'joke_text': joke_text
                })
            except:
                continue  # Saltar chistes que causen error
        
        # Ordenar por rating predicho (descendente) y tomar top_n
        recommendations = sorted(predictions, key=lambda x: x['predicted_rating'], reverse=True)[:top_n]
        
        return jsonify({
            "user_id": user_id,
            "recommendations": recommendations,
            "user_bias": round(user_bias, 3),
            "user_ratings_count": len(user_ratings.get(user_id, [])),
            "total_jokes_evaluated": len(predictions)
        })
        
    except ValueError:
        return jsonify({"error": "user_id debe ser un número entero"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/user/ratings", methods=["GET"])
def get_user_ratings():
    """Obtener las últimas clasificaciones de un usuario"""
    try:
        user_id = int(request.args.get("user_id"))
        
        if user_id not in user_ratings:
            return jsonify({
                "user_id": user_id,
                "ratings": [],
                "total_ratings": 0,
                "message": "Usuario sin clasificaciones previas"
            })
        
        # Convertir a formato legible
        ratings_list = []
        for joke_id, rating, timestamp in user_ratings[user_id]:
            # Obtener texto del chiste si está disponible
            joke_text = "N/A"
            if jokes_df is not None:
                try:
                    joke_text = jokes_df[jokes_df['joke_id'] == joke_id]['joke_text'].iloc[0]
                except:
                    pass
            
            ratings_list.append({
                "joke_id": joke_id,
                "rating": rating,
                "timestamp": timestamp,
                "joke_text": joke_text[:100] + "..." if len(joke_text) > 100 else joke_text
            })
        
        return jsonify({
            "user_id": user_id,
            "ratings": ratings_list,
            "total_ratings": len(ratings_list),
            "average_rating": round(sum(r["rating"] for r in ratings_list) / len(ratings_list), 2) if ratings_list else 0
        })
        
    except ValueError:
        return jsonify({"error": "user_id debe ser un número entero"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    """Obtener estadísticas generales del sistema"""
    total_users = len(user_ratings)
    total_ratings = sum(len(ratings) for ratings in user_ratings.values())
    
    return jsonify({
        "total_users_with_ratings": total_users,
        "total_ratings_stored": total_ratings,
        "jokes_available": len(jokes_df) if jokes_df is not None else 0,
        "model_loaded": model is not None,
        "data_loaded": jokes_df is not None
    })

if __name__ == "__main__":
    print("🚀 Iniciando API de Recomendación de Chistes...")
    print("📊 Funcionalidades:")
    print("   - Predicciones personalizadas basadas en historial")
    print("   - Almacenamiento de últimas 3 clasificaciones por usuario")
    print("   - Recomendaciones ajustadas por preferencias del usuario")
    print("   - Persistencia de datos en user_ratings.json")
    print(f"🌐 Servidor corriendo en http://127.0.0.1:5017")
    
    app.run(debug=True, host="127.0.0.1", port=5017) 

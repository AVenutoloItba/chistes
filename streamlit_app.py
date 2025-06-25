import streamlit as st
import pandas as pd
import requests
import json
import random
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="🎭 Recomendador de Chistes",
    page_icon="😂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URLs de la API
API_BASE_URL = "http://127.0.0.1:5017"

# Archivo para guardar perfiles de usuarios
USER_PROFILES_FILE = "user_profiles.csv"

@st.cache_data
def load_jokes():
    """Cargar el dataset de chistes"""
    try:
        jokes_df = pd.read_csv("jokes.csv")
        return jokes_df
    except FileNotFoundError:
        st.error("❌ No se encontró el archivo jokes.csv")
        return None

def send_rating_to_api(user_id, joke_id, rating):
    """Enviar clasificación a la API"""
    try:
        payload = {
            "user_id": int(user_id),  # Convertir a int nativo de Python
            "joke_id": int(joke_id),  # Convertir a int nativo de Python
            "rating": float(rating)   # Convertir a float nativo de Python
        }
        
        response = requests.post(f"{API_BASE_URL}/rate/joke", json=payload, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error enviando clasificación: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con la API: {e}")
        return None

def get_user_ratings(user_id):
    """Obtener las clasificaciones del usuario"""
    try:
        response = requests.get(f"{API_BASE_URL}/user/ratings", 
                              params={"user_id": int(user_id)}, timeout=5)  # Convertir a int
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"ratings": [], "total_ratings": 0}
            
    except requests.exceptions.RequestException:
        return {"ratings": [], "total_ratings": 0}

def get_recommendation(user_id, top_n=1):
    """Obtener recomendaciones de la API"""
    try:
        response = requests.get(f"{API_BASE_URL}/recommend/jokes", 
                              params={"user_id": int(user_id), "top_n": int(top_n)}, timeout=10)  # Convertir a int
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            st.error(f"Error obteniendo recomendación: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con la API: {e}")
        return None

def get_predicted_rating(user_id, joke_id):
    """Obtener la predicción de rating para un chiste específico"""
    try:
        response = requests.get(f"{API_BASE_URL}/predict/jokes", 
                              params={"user_id": int(user_id), "joke_id": int(joke_id)}, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except requests.exceptions.RequestException:
        return None

def get_system_stats():
    """Obtener estadísticas del sistema para ayudar con IDs únicos"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=3)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def suggest_unique_id():
    """Sugerir un ID único basado en estadísticas del sistema"""
    stats = get_system_stats()
    if stats:
        # Usar el número de usuarios + un offset para sugerir ID
        base_id = stats.get("total_users_with_ratings", 0) + 1000
        return base_id + random.randint(1, 99)
    else:
        # Fallback si no hay API
        return random.randint(2000, 9999)

def check_api_status():
    """Verificar si la API está funcionando"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=3)
        return response.status_code == 200
    except:
        return False

def load_user_profiles():
    """Cargar perfiles de usuarios desde CSV"""
    try:
        if os.path.exists(USER_PROFILES_FILE):
            return pd.read_csv(USER_PROFILES_FILE)
        else:
            # Crear DataFrame vacío con las columnas necesarias
            return pd.DataFrame(columns=[
                'user_id', 'edad', 'genero', 'nacionalidad', 'profesion', 
                'fecha_creacion', 'ultima_actualizacion'
            ])
    except Exception as e:
        st.error(f"Error cargando perfiles: {e}")
        return pd.DataFrame(columns=[
            'user_id', 'edad', 'genero', 'nacionalidad', 'profesion', 
            'fecha_creacion', 'ultima_actualizacion'
        ])

def save_user_profile(user_id, edad, genero, nacionalidad, profesion):
    """Guardar o actualizar perfil de usuario en CSV"""
    try:
        # Cargar perfiles existentes
        profiles_df = load_user_profiles()
        
        # Crear timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar si el usuario ya existe
        if user_id in profiles_df['user_id'].values:
            # Actualizar perfil existente
            mask = profiles_df['user_id'] == user_id
            profiles_df.loc[mask, 'edad'] = edad
            profiles_df.loc[mask, 'genero'] = genero
            profiles_df.loc[mask, 'nacionalidad'] = nacionalidad
            profiles_df.loc[mask, 'profesion'] = profesion
            profiles_df.loc[mask, 'ultima_actualizacion'] = timestamp
            action = "actualizado"
        else:
            # Crear nuevo perfil
            new_profile = pd.DataFrame({
                'user_id': [user_id],
                'edad': [edad],
                'genero': [genero],
                'nacionalidad': [nacionalidad],
                'profesion': [profesion],
                'fecha_creacion': [timestamp],
                'ultima_actualizacion': [timestamp]
            })
            profiles_df = pd.concat([profiles_df, new_profile], ignore_index=True)
            action = "creado"
        
        # Guardar en CSV
        profiles_df.to_csv(USER_PROFILES_FILE, index=False)
        return action
        
    except Exception as e:
        st.error(f"Error guardando perfil: {e}")
        return None

def get_user_profile(user_id):
    """Obtener perfil de un usuario específico"""
    try:
        profiles_df = load_user_profiles()
        user_profile = profiles_df[profiles_df['user_id'] == user_id]
        
        if not user_profile.empty:
            return user_profile.iloc[0].to_dict()
        else:
            return None
    except Exception as e:
        st.error(f"Error obteniendo perfil: {e}")
        return None

def get_profile_statistics():
    """Obtener estadísticas de los perfiles de usuarios"""
    try:
        profiles_df = load_user_profiles()
        
        if profiles_df.empty:
            return None
        
        stats = {
            'total_usuarios': len(profiles_df),
            'edad_promedio': profiles_df['edad'].mean() if 'edad' in profiles_df.columns else 0,
            'generos': profiles_df['genero'].value_counts().to_dict() if 'genero' in profiles_df.columns else {},
            'nacionalidades': profiles_df['nacionalidad'].value_counts().to_dict() if 'nacionalidad' in profiles_df.columns else {},
            'profesiones': profiles_df['profesion'].value_counts().to_dict() if 'profesion' in profiles_df.columns else {}
        }
        
        return stats
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {e}")
        return None

# Cargar datos
jokes_df = load_jokes()

# Título principal
st.title("🎭 Recomendador de Chistes Inteligente")

# Información del equipo
st.markdown("""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 30px;'>
    <h3 style='text-align: center; color: #000000;'>👥 Equipo de Desarrollo</h3>
    <p style='text-align: center; font-size: 18px; margin-bottom: 5px; color: #000000;'>
        <strong>Agustin Venutolo</strong> • <strong>Bautista Rios</strong> • <strong>Tomas Attas</strong>
    </p>
</div>
""", unsafe_allow_html=True)

# Verificar estado de la API
api_status = check_api_status()
if api_status:
    st.success("✅ API conectada y funcionando correctamente")
else:
    st.error("❌ API no disponible. Ejecuta: `python jokes_api.py`")

# Verificar si hay datos
if jokes_df is not None:
    total_jokes = len(jokes_df)
    st.info(f"📚 Dataset cargado: **{total_jokes} chistes** disponibles")
    
    # Inicializar estado de sesión
    if 'current_joke_id' not in st.session_state:
        st.session_state.current_joke_id = jokes_df.sample(1)['joke_id'].iloc[0]
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = 1
    
    # Nuevo: historial de chistes ya mostrados
    if 'viewed_jokes' not in st.session_state:
        st.session_state.viewed_jokes = set()
    
    # Agregar chiste actual al historial si no está
    if st.session_state.current_joke_id not in st.session_state.viewed_jokes:
        st.session_state.viewed_jokes.add(st.session_state.current_joke_id)
    
    # Sidebar para configuración de usuario
    with st.sidebar:
        st.header("👤 Configuración de Usuario")
        
        # Seleccionar modo: usar existente o crear nuevo
        user_mode = st.radio(
            "¿Qué deseas hacer?",
            ["🔑 Usar Usuario Existente", "🆕 Crear Nuevo Usuario"],
            help="Elige si quieres usar un ID existente o crear uno nuevo"
        )
        
        if user_mode == "🔑 Usar Usuario Existente":
            # Input para User ID existente
            user_id = st.number_input(
                "ID de Usuario:",
                min_value=1,
                max_value=10000,
                value=st.session_state.user_id,
                help="Ingresa tu ID único de usuario existente"
            )
            st.session_state.user_id = user_id
            
        else:  # Crear nuevo usuario
            st.subheader("🆕 Crear Nuevo Usuario")
            
            # Opciones para crear usuario
            creation_mode = st.selectbox(
                "¿Cómo quieres crear tu usuario?",
                ["🎲 Generar ID Automáticamente", "✏️ Elegir ID Personalizado"]
            )
            
            if creation_mode == "🎲 Generar ID Automáticamente":
                col_gen1, col_gen2 = st.columns(2)
                
                with col_gen1:
                    if st.button("🎰 Generar ID Aleatorio", type="primary"):
                        # Generar un ID aleatorio que no esté en uso
                        new_id = suggest_unique_id()
                        st.session_state.user_id = new_id
                        st.session_state.viewed_jokes = set()  # Nuevo usuario, historial limpio
                        st.success(f"✅ Nuevo Usuario ID: {new_id}")
                        st.balloons()
                        st.rerun()
                
                with col_gen2:
                    if st.button("🔢 Generar ID Inteligente"):
                        # Generar ID basado en estadísticas del sistema
                        if api_status:
                            stats = get_system_stats()
                            if stats:
                                new_id = stats.get("total_users_with_ratings", 0) + 1001
                                st.session_state.user_id = new_id
                                st.session_state.viewed_jokes = set()
                                st.success(f"✅ Nuevo Usuario ID: {new_id} (basado en {stats.get('total_users_with_ratings', 0)} usuarios existentes)")
                                st.balloons()
                                st.rerun()
                            else:
                                new_id = random.randint(100, 999)
                                st.session_state.user_id = new_id
                                st.session_state.viewed_jokes = set()
                                st.success(f"✅ Nuevo Usuario ID: {new_id}")
                                st.rerun()
                        else:
                            st.error("🔌 Necesitas conexión a la API para generar ID inteligente")
                
                st.info("💡 Los IDs generados automáticamente son únicos y fáciles de recordar")
                
            else:  # Elegir ID personalizado
                custom_id = st.number_input(
                    "Elige tu ID personalizado:",
                    min_value=1,
                    max_value=10000,
                    value=1001,
                    help="Elige un número que te guste como tu ID único"
                )
                
                col_custom1, col_custom2 = st.columns(2)
                
                with col_custom1:
                    if st.button("✅ Crear Usuario", type="primary"):
                        st.session_state.user_id = custom_id
                        st.session_state.viewed_jokes = set()  # Nuevo usuario, historial limpio
                        st.success(f"✅ Usuario {custom_id} creado exitosamente!")
                        st.balloons()
                        st.rerun()
                
                with col_custom2:
                    if st.button("🔍 Verificar Disponibilidad"):
                        # Verificar si el ID está en uso (simulado)
                        if api_status:
                            user_data = get_user_ratings(custom_id)
                            if user_data.get("total_ratings", 0) > 0:
                                st.warning(f"⚠️ ID {custom_id} ya tiene datos")
                            else:
                                st.success(f"✅ ID {custom_id} disponible")
                        else:
                            st.info("🔍 Verificación disponible cuando API esté conectada")
        
        # Mostrar información del usuario actual
        st.markdown("---")
        st.subheader(f"👤 Usuario Actual: {st.session_state.user_id}")
        
        # Información del usuario actual
        if st.session_state.user_id:
            st.info(f"🆔 Tu ID: **{st.session_state.user_id}**")
            
            # Botón para cambiar de usuario
            if st.button("🔄 Cambiar Usuario", help="Cambiar a otro usuario o crear uno nuevo"):
                # Reiniciar algunas variables para el cambio de usuario
                st.session_state.viewed_jokes = set()
                st.success("✅ Listo para cambiar de usuario")
                st.rerun()
        
        # === NUEVA SECCIÓN: PERFIL DEMOGRÁFICO ===
        st.markdown("---")
        st.subheader("👤 Perfil Demográfico")
        
        # Obtener perfil existente
        current_profile = get_user_profile(st.session_state.user_id)
        
        if current_profile:
            # Mostrar perfil existente
            st.success("✅ Perfil encontrado")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.metric("👶 Edad", f"{current_profile['edad']} años")
                st.metric("🌍 Nacionalidad", current_profile['nacionalidad'])
            with col_p2:
                st.metric("⚧️ Género", current_profile['genero'])
                st.metric("💼 Profesión", current_profile['profesion'])
            
            st.caption(f"📅 Creado: {current_profile.get('fecha_creacion', 'N/A')}")
            
            # Opción para editar perfil
            with st.expander("✏️ Editar Perfil"):
                edit_profile = True
        else:
            # No hay perfil, mostrar formulario de creación
            st.warning("⚠️ No tienes perfil demográfico")
            st.info("💡 Completa tu perfil para obtener recomendaciones más personalizadas")
            edit_profile = True
        
        # Formulario para crear/editar perfil
        if 'edit_profile' in locals() and edit_profile:
            st.subheader("📝 Datos Demográficos")
            
            # Valores por defecto del perfil existente o vacíos
            default_edad = current_profile['edad'] if current_profile else 25
            default_genero = current_profile['genero'] if current_profile else "Prefiero no decir"
            default_nacionalidad = current_profile['nacionalidad'] if current_profile else "Argentina"
            default_profesion = current_profile['profesion'] if current_profile else "Estudiante"
            
            # Campos del formulario
            edad = st.number_input(
                "👶 Edad:",
                min_value=13,
                max_value=100,
                value=default_edad,
                help="Tu edad en años"
            )
            
            genero = st.selectbox(
                "⚧️ Género:",
                ["Masculino", "Femenino", "No binario", "Prefiero no decir", "Otro"],
                index=["Masculino", "Femenino", "No binario", "Prefiero no decir", "Otro"].index(default_genero) if default_genero in ["Masculino", "Femenino", "No binario", "Prefiero no decir", "Otro"] else 3
            )
            
            nacionalidad = st.selectbox(
                "🌍 Nacionalidad:",
                [
                    "Argentina", "Brasil", "Chile", "Colombia", "México", "Perú", "Uruguay", "Venezuela",
                    "España", "Estados Unidos", "Canadá", "Reino Unido", "Francia", "Alemania", "Italia",
                    "China", "Japón", "India", "Australia", "Otro"
                ],
                index=[
                    "Argentina", "Brasil", "Chile", "Colombia", "México", "Perú", "Uruguay", "Venezuela",
                    "España", "Estados Unidos", "Canadá", "Reino Unido", "Francia", "Alemania", "Italia",
                    "China", "Japón", "India", "Australia", "Otro"
                ].index(default_nacionalidad) if default_nacionalidad in [
                    "Argentina", "Brasil", "Chile", "Colombia", "México", "Perú", "Uruguay", "Venezuela",
                    "España", "Estados Unidos", "Canadá", "Reino Unido", "Francia", "Alemania", "Italia",
                    "China", "Japón", "India", "Australia", "Otro"
                ] else 0
            )
            
            profesion = st.selectbox(
                "💼 Profesión:",
                [
                    "Estudiante", "Ingeniero/a", "Médico/a", "Profesor/a", "Abogado/a", "Artista",
                    "Diseñador/a", "Programador/a", "Científico/a", "Emprendedor/a", "Comerciante",
                    "Funcionario/a público", "Jubilado/a", "Trabajador/a independiente", "Otro"
                ],
                index=[
                    "Estudiante", "Ingeniero/a", "Médico/a", "Profesor/a", "Abogado/a", "Artista",
                    "Diseñador/a", "Programador/a", "Científico/a", "Emprendedor/a", "Comerciante",
                    "Funcionario/a público", "Jubilado/a", "Trabajador/a independiente", "Otro"
                ].index(default_profesion) if default_profesion in [
                    "Estudiante", "Ingeniero/a", "Médico/a", "Profesor/a", "Abogado/a", "Artista",
                    "Diseñador/a", "Programador/a", "Científico/a", "Emprendedor/a", "Comerciante",
                    "Funcionario/a público", "Jubilado/a", "Trabajador/a independiente", "Otro"
                ] else 0
            )
            
            # Botón para guardar perfil
            if st.button("💾 Guardar Perfil", type="primary"):
                action = save_user_profile(st.session_state.user_id, edad, genero, nacionalidad, profesion)
                if action:
                    st.success(f"✅ Perfil {action} exitosamente!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Error guardando el perfil")
        
        # Mostrar estadísticas de perfiles (si hay datos)
        profile_stats = get_profile_statistics()
        if profile_stats and profile_stats['total_usuarios'] > 0:
            st.markdown("---")
            st.subheader("📊 Estadísticas de la Comunidad")
            
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.metric("👥 Usuarios Registrados", profile_stats['total_usuarios'])
                st.metric("🎂 Edad Promedio", f"{profile_stats['edad_promedio']:.1f} años")
            
            with col_stats2:
                # Género más común
                if profile_stats['generos']:
                    genero_popular = max(profile_stats['generos'], key=profile_stats['generos'].get)
                    st.metric("⚧️ Género Predominante", genero_popular)
                
                # Nacionalidad más común
                if profile_stats['nacionalidades']:
                    nacionalidad_popular = max(profile_stats['nacionalidades'], key=profile_stats['nacionalidades'].get)
                    st.metric("🌍 Nacionalidad Común", nacionalidad_popular)
        
        # Mostrar información de chistes vistos
        st.subheader("👁️ Progreso de Visualización")
        viewed_count = len(st.session_state.viewed_jokes)
        total_jokes = len(jokes_df)
        progress = viewed_count / total_jokes if total_jokes > 0 else 0
        
        st.metric("Chistes Vistos", f"{viewed_count}/{total_jokes}")
        st.progress(progress)
        
        if viewed_count > 0:
            percentage = (viewed_count / total_jokes) * 100
            st.write(f"📈 Has visto el {percentage:.1f}% de todos los chistes")
        
        # Botón para reiniciar historial
        if viewed_count > 0:
            if st.button("🔄 Reiniciar Historial de Vistos", help="Permite volver a ver todos los chistes"):
                st.session_state.viewed_jokes = set()
                st.success("✅ Historial reiniciado")
                st.rerun()
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("😄 Chiste Actual")
        
        # Mostrar el chiste actual
        current_joke = jokes_df[jokes_df['joke_id'] == st.session_state.current_joke_id]
        if not current_joke.empty:
            joke_text = current_joke['joke_text'].iloc[0]
            
            # Obtener predicción si la API está disponible
            predicted_data = None
            if api_status:
                predicted_data = get_predicted_rating(st.session_state.user_id, st.session_state.current_joke_id)
            
            # Mostrar el texto del chiste en una caja destacada
            st.markdown(f"""
            <div style='background-color: #ffe8e8; padding: 25px; border-radius: 15px; 
                        border-left: 5px solid #dc3545; margin: 20px 0;'>
                <h4 style='color: #dc3545; margin-bottom: 15px;'>
                    🎯 Chiste #{st.session_state.current_joke_id}
                </h4>
                <p style='font-size: 16px; line-height: 1.6; margin: 0; color: black;'>
                    {joke_text}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostrar predicción si está disponible
            if predicted_data:
                col_pred1, col_pred2, col_pred3 = st.columns(3)
                
                with col_pred1:
                    st.metric(
                        "🤖 Rating Predicho", 
                        f"{predicted_data.get('predicted_rating', 0):.1f}/10",
                        help="Lo que el sistema predice que calificarías este chiste"
                    )
                
                # with col_pred2:
                #     st.metric(
                #         "📊 Predicción Base", 
                #         f"{predicted_data.get('base_prediction', 0):.1f}",
                #         help="Predicción del modelo SVD sin ajustes personales"
                #     )
                
                # with col_pred3:
                #     user_bias = predicted_data.get('user_bias', 0)
                #     bias_emoji = "😊" if user_bias > 0 else "🤔" if user_bias < 0 else "😐"
                #     st.metric(
                #         f"{bias_emoji} Tu Sesgo", 
                #         f"{user_bias:+.1f}",
                #         help="Ajuste basado en tus calificaciones previas (+optimista, -exigente)"
                #     )
                
                # Mostrar información adicional
                if predicted_data.get('user_ratings_count', 0) > 0:
                    st.info(f"💡 Predicción basada en {predicted_data['user_ratings_count']} calificaciones tuyas")
                else:
                    st.warning("⚠️ Predicción genérica - califica algunos chistes para personalizar")
            
            elif api_status:
                st.info("🔄 Cargando predicción...")
            else:
                st.warning("❌ Predicción no disponible - API desconectada")
            
            # Sistema de calificación
            st.subheader("⭐ Califica este chiste")
            rating = st.slider(
                "¿Qué tan gracioso te pareció?",
                min_value=-10.0,
                max_value=10.0,
                value=5.0,
                step=0.5,
                help="0 = Nada gracioso, 10 = Muy gracioso"
            )
            
            # Botones de acción
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("📝 Guardar Calificación", type="primary"):
                    if api_status:
                        result = send_rating_to_api(st.session_state.user_id, st.session_state.current_joke_id, rating)
                        if result:
                            st.success(f"✅ Calificación guardada: {rating}/10")
                            st.balloons()
                            # Recargar datos del usuario
                            st.rerun()
                        else:
                            st.error("❌ Error guardando la calificación")
                    else:
                        st.error("❌ API no disponible")
            
            with col_btn2:
                if st.button("🎲 Otro Chiste"):
                    # Seleccionar un chiste aleatorio diferente
                    available_jokes = jokes_df[jokes_df['joke_id'] != st.session_state.current_joke_id]
                    if not available_jokes.empty:
                        st.session_state.current_joke_id = available_jokes.sample(1)['joke_id'].iloc[0]
                        st.rerun()
            
            with col_btn3:
                if st.button("🎯 Recomendación Inteligente"):
                    if api_status:
                        with st.spinner("🤖 Analizando tus preferencias..."):
                            # Obtener más recomendaciones para filtrar las ya vistas
                            recommendation = get_recommendation(st.session_state.user_id, top_n=10)
                            
                        if recommendation and recommendation.get("recommendations"):
                            # Filtrar chistes ya vistos
                            unviewed_jokes = [
                                joke for joke in recommendation["recommendations"]
                                if joke["joke_id"] not in st.session_state.viewed_jokes
                            ]
                            
                            if unviewed_jokes:
                                # Tomar el mejor chiste no visto
                                best_joke = unviewed_jokes[0]
                                st.session_state.current_joke_id = best_joke["joke_id"]
                                st.session_state.viewed_jokes.add(best_joke["joke_id"])
                                
                                # Mostrar información de la recomendación
                                position = len(st.session_state.viewed_jokes)
                                st.success(f"🎯 ¡Recomendación #{position}! (Rating predicho: {best_joke['predicted_rating']:.1f})")
                                
                                # Mostrar detalles adicionales
                                if recommendation.get("user_bias") != 0:
                                    bias_text = "optimista" if recommendation["user_bias"] > 0 else "exigente"
                                    st.info(f"📊 Basado en tu historial, eres un usuario {bias_text}")
                                
                                st.rerun()
                            else:
                                # Si ya vio todos los chistes recomendados
                                if len(st.session_state.viewed_jokes) >= len(jokes_df):
                                    st.warning("🎉 ¡Has visto todos los chistes! Reiniciando historial...")
                                    st.session_state.viewed_jokes = set()
                                    st.session_state.current_joke_id = jokes_df.sample(1)['joke_id'].iloc[0]
                                    st.rerun()
                                else:
                                    st.info("🔄 Obteniendo más recomendaciones...")
                                    # Obtener todas las recomendaciones disponibles
                                    all_recommendations = get_recommendation(st.session_state.user_id, top_n=len(jokes_df))
                                    if all_recommendations:
                                        all_unviewed = [
                                            joke for joke in all_recommendations["recommendations"]
                                            if joke["joke_id"] not in st.session_state.viewed_jokes
                                        ]
                                        if all_unviewed:
                                            best_joke = all_unviewed[0]
                                            st.session_state.current_joke_id = best_joke["joke_id"]
                                            st.session_state.viewed_jokes.add(best_joke["joke_id"])
                                            st.rerun()
                        else:
                            st.error("❌ No se pudo obtener recomendación")
                    else:
                        st.error("❌ API no disponible para recomendaciones")
    
    with col2:
        st.header("🎯 Mejores Recomendaciones")
        
        if api_status and st.button("📋 Ver Top 5"):
            with st.spinner("🔍 Buscando los mejores chistes para ti..."):
                recommendations = get_recommendation(st.session_state.user_id, top_n=5)
                
            if recommendations and recommendations.get("recommendations"):
                st.subheader("🏆 Tus Top 5 Chistes")
                
                for i, joke in enumerate(recommendations["recommendations"], 1):
                    with st.expander(f"#{i} - Rating: {joke['predicted_rating']:.1f}/10"):
                        st.write(joke["joke_text"])
                        if st.button(f"Ver este chiste", key=f"view_{joke['joke_id']}"):
                            st.session_state.current_joke_id = joke["joke_id"]
                            st.rerun()
                
                # Información adicional
                st.info(f"📊 Evaluados {recommendations.get('total_jokes_evaluated', 0)} chistes")
                
                if recommendations.get("user_ratings_count", 0) >= 3:
                    st.success("🎓 ¡Tienes suficientes calificaciones para recomendaciones personalizadas!")
                else:
                    remaining = 3 - recommendations.get("user_ratings_count", 0)
                    st.warning(f"⏳ Califica {remaining} chistes más para mejores recomendaciones")
        
        # Estadísticas generales
        if api_status:
            try:
                stats_response = requests.get(f"{API_BASE_URL}/stats", timeout=3)
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    
                    st.subheader("📈 Estadísticas del Sistema")
                    st.metric("Usuarios Activos", stats.get("total_users_with_ratings", 0))
                    st.metric("Total Calificaciones", stats.get("total_ratings_stored", 0))
                    st.metric("Chistes Disponibles", stats.get("jokes_available", 0))
            except:
                pass
        
        # Mostrar perfil del usuario actual
       
            
            # Mostrar estadísticas de calificaciones si la API está disponible
            if api_status:
                user_data = get_user_ratings(st.session_state.user_id)
                if user_data.get("total_ratings", 0) > 0:
                    st.subheader("📊 Tu Historial de Calificaciones")
                    
                    col_hist1, col_hist2, col_hist3 = st.columns(3)
                    with col_hist1:
                        st.metric("🎭 Chistes Calificados", user_data.get("total_ratings", 0))
                    with col_hist2:
                        avg_rating = user_data.get("average_rating", 0)
                        st.metric("⭐ Rating Promedio", f"{avg_rating:.1f}/10")
                    with col_hist3:
                        # Calcular tendencia del usuario
                        if avg_rating > 6:
                            tendency = "😊 Optimista"
                        elif avg_rating < 4:
                            tendency = "🤔 Exigente"
                        else:
                            tendency = "😐 Neutral"
                        st.metric("🎯 Tendencia", tendency)
                    
                    # Mostrar últimas calificaciones en expander
                    if user_data.get("ratings"):
                        with st.expander("🕒 Ver Últimas Calificaciones"):
                            for rating in user_data["ratings"]:
                                col_rating1, col_rating2 = st.columns([3, 1])
                                with col_rating1:
                                    st.write(f"**Chiste {rating['joke_id']}**: {rating['joke_text'][:50]}...")
                                with col_rating2:
                                    st.write(f"⭐ {rating['rating']}/10")
        else:
            # Si no hay perfil, mostrar mensaje motivador
            st.info("💡 **¡Completa tu perfil demográfico!** Ve al sidebar para agregar tu información y obtener recomendaciones más personalizadas.")
            
            # Mostrar beneficios de completar el perfil
            st.markdown("""
            ### 🎯 Beneficios de completar tu perfil:
            
            - **🎭 Recomendaciones más precisas** basadas en tu demografía
            - **📊 Análisis personalizado** de tus preferencias
            - **🌍 Comparación** con usuarios similares
            - **📈 Estadísticas** de la comunidad
            """)
    
    # Información sobre el sistema
    st.markdown("---")
    
    st.markdown("""
    ### 🤖 ¿Cómo funciona la recomendación inteligente?
    
    - **Aprendizaje Personalizado**: El sistema aprende de tus últimas 3 calificaciones
    - **Predicción Avanzada**: Usa un modelo SVD para predecir qué chistes te gustarán más
    - **Ajuste Dinámico**: Se adapta a si eres más optimista o exigente en tus calificaciones
    - **Persistencia**: Tus calificaciones se guardan para futuras sesiones
    - **📊 Análisis Demográfico**: Considera tu edad, género, nacionalidad y profesión
    
    💡 **Tip**: Califica al menos 3 chistes y completa tu perfil para obtener recomendaciones más precisas
    """)

else:
    st.error("❌ No se pudo cargar el dataset de chistes. Asegúrate de que existe el archivo 'jokes.csv'")

# Footer
st.markdown("---")
st.caption("🎭 Aplicación desarrollada con Streamlit 🚀 | Sistema de Recomendación Inteligente") 

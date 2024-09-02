from flask import Flask, render_template, request, send_file
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import numpy as np
import pickle
import io
from fpdf import FPDF

# Specify the location of the templates folder
app = Flask(__name__, template_folder='Static/templates', static_folder='Static')

# Load Datasets
data_symptoms = pd.read_csv("Datasets/symtoms_df.csv")
data_medication = pd.read_csv("Datasets/medications.csv")
data_diets = pd.read_csv("Datasets/diets.csv")
data_description = pd.read_csv("Datasets/description.csv")
data_precaution = pd.read_csv("Datasets/precautions_df.csv")
precautions = ['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']
data_workout = pd.read_csv("Datasets/workout_df.csv")
df = pd.read_csv("Datasets/Training.csv")

# Data Filtering
X = df.drop('prognosis', axis=1)
y = df['prognosis']

# Load Model
svc_production = pickle.load(open('Models/production_model.pkl', 'rb'))

# Feature Engineering - Label Encoding
encoder = LabelEncoder()
encoder.fit(y)
Y = encoder.transform(y)

# Mapping of encoded values to original labels
label_mapping = dict(enumerate(encoder.classes_))

# Making dict for individual symptoms
symptoms = list(df.columns)
symptoms_dict = {element: index for index, element in enumerate(symptoms) if index < len(symptoms) - 1}

# Symptom_Categories 
symptom_categories = {
    'Skin-related Symptoms': ['itching', 'skin_rash', 'nodal_skin_eruptions', 'dischromic_patches'],
    'Respiratory Symptoms': ['continuous_sneezing', 'shivering', 'chills', 'fatigue', 'cough'],
    'Gastrointestinal Symptoms': ['stomach_pain', 'vomiting', 'indigestion', 'stomach_bleeding'],
    'Pain-related Symptoms': ['joint_pain', 'back_pain', 'muscle_wasting', 'stiff_neck'],
    'Neurological Symptoms': ['headache', 'dizziness', 'loss_of_balance', 'slurred_speech'],
    'Urinary Symptoms': ['burning_micturition', 'spotting_urination'],
    'Emotional/Mental Symptoms': ['anxiety', 'depression', 'irritability', 'mood_swings'],
    'Other Symptoms': ['high_fever', 'sweating', 'weight_loss']
}

# Model Prediction function
def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptoms_dict))
    for item in patient_symptoms:
        if item in symptoms_dict:
            input_vector[symptoms_dict[item]] = 1
    return label_mapping[svc_production.predict([input_vector])[0]]

# Method prediction for individual diagnostic
def get_everything(predicted_disease):
    user_disease_description_list = None
    user_disease_precaution_list = None
    user_disease_medication_list = None
    user_disease_diets_list = None
    user_disease_workout_list = None

    # Retrieve the description
    if predicted_disease in data_description['Disease'].values:
        user_disease_description = data_description.loc[data_description['Disease'] == predicted_disease, 'Description'].values[0]
        user_disease_description_list = user_disease_description.strip(".")

    # Retrieve the precautions
    if predicted_disease in data_precaution['Disease'].values:
        user_disease_precaution = data_precaution.loc[data_precaution['Disease'] == predicted_disease, precautions].values[0]
        user_disease_precaution_list = [pre for pre in user_disease_precaution if pd.notna(pre)]

    # Retrieve the medication
    if predicted_disease in data_medication['Disease'].values:
        user_disease_medication = data_medication.loc[data_medication['Disease'] == predicted_disease, 'Medication'].values[0]
        user_disease_medication_list = user_disease_medication.strip(".")

    # Retrieve the diet
    if predicted_disease in data_diets['Disease'].values:
        user_disease_diets = data_diets.loc[data_diets['Disease'] == predicted_disease, 'Diet'].values[0]
        user_disease_diets_list = eval(user_disease_diets) if isinstance(user_disease_diets, str) else [food for food in user_disease_diets if pd.notna(food)]

    # Retrieve the workout
    if predicted_disease in data_workout['disease'].values:
        user_disease_workout = data_workout.loc[data_workout['disease'] == predicted_disease, 'workout'].values
        user_disease_workout_list = [w for w in user_disease_workout if pd.notna(w)]

    return user_disease_description_list, user_disease_precaution_list, user_disease_medication_list, user_disease_diets_list, user_disease_workout_list

@app.route('/')
def home():
    return render_template('Home_page.html')

@app.route('/about')
def about():
    return render_template('About.html')

@app.route('/curetrack')
def curetrack():
    return render_template('CureTrack.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        selected_symptoms = request.form.getlist('symptoms')
        user_symptom = [sym.strip() for sym in selected_symptoms]
        predicted_disease = get_predicted_value(user_symptom)
        des, pre, med, diet, workout = get_everything(predicted_disease)
        
        return render_template(
            'cureTrack.html', 
            predicted_disease=predicted_disease,
            disease_description=des,
            disease_medication=med,
            disease_diet=diet,
            disease_workout=workout,
            disease_precaution=pre
        )
        
@app.context_processor
def inject_symptom_categories():
    return dict(symptom_categories=symptom_categories)

# PDF Generation Function
def generate_pdf(predicted_disease, des, pre, med, diet, workout):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Diagnosis Result", ln=True, align="C")
    
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Disease: {predicted_disease}", ln=True)
    pdf.cell(200, 10, txt=f"Description: {des}", ln=True)
    pdf.cell(200, 10, txt=f"Medication: {med}", ln=True)
    pdf.cell(200, 10, txt=f"Diet: {', '.join(diet)}", ln=True)
    pdf.cell(200, 10, txt=f"Workout: {', '.join(workout)}", ln=True)
    pdf.cell(200, 10, txt=f"Precautions: {', '.join(pre)}", ln=True)
    
    return pdf

@app.route('/download_prescription', methods=['POST'])
def download_prescription():
    try:
        predicted_disease = request.form['predicted_disease']
        des = request.form.get('disease_description', 'N/A')
        pre = request.form.get('disease_precaution', 'N/A').split(',')
        med = request.form.get('disease_medication', 'N/A')
        diet = request.form.get('disease_diet', 'N/A').split(',')
        workout = request.form.get('disease_workout', 'N/A').split(',')
        
        pdf = generate_pdf(predicted_disease, des, pre, med, diet, workout)
        
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        
        return send_file(pdf_output, as_attachment=True, download_name="prescription.pdf")
    except Exception as e:
        return str(e), 500
    
if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import requests
import os

app = Flask(__name__)

FASTAPI_URL = "http://localhost:8000"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-bill', methods=['POST'])
def process_bill():
    try:
        file = request.files.get('bill_image')
        instruction = request.form.get('instruction', 'Split equally among 2')
        
        if not file:
            return jsonify({"error": "No file uploaded"}), 400
        
        files = {'file': (file.filename, file.stream, file.content_type)}
        data = {'instruction': instruction}
        
        response = requests.post(f"{FASTAPI_URL}/process-bill", files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return redirect(url_for('view_result', bill_id=result['bill_id']))
        else:
            return jsonify({"error": f"Backend error: {response.json()}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/result/<bill_id>')
def view_result(bill_id):
    try:
        response = requests.get(f"{FASTAPI_URL}/bill/{bill_id}")
        
        if response.status_code == 200:
            bill_data = response.json()
            return render_template('result.html', 
                                 bill_id=bill_id,
                                 bill_json=bill_data)
        else:
            return jsonify({"error": "Bill not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/lookup')
def lookup():
    return render_template('lookup.html')

@app.route('/lookup-bill', methods=['POST'])
def lookup_bill():
    try:
        bill_id = request.form.get('bill_id')
        
        if not bill_id:
            return jsonify({"error": "No bill ID provided"}), 400
        
        return redirect(url_for('view_result', bill_id=bill_id))
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<bill_id>')
def download_bill(bill_id):
    try:
        response = requests.get(f"{FASTAPI_URL}/bill/{bill_id}/download", stream=True)
        
        if response.status_code == 200:
            # Save temporarily and send
            temp_path = f"/tmp/bill_{bill_id}.jpg"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            return send_file(temp_path, as_attachment=True, download_name=f"bill_{bill_id}.jpg")
        else:
            return jsonify({"error": "Bill not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

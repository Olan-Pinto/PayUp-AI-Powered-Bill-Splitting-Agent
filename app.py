# from flask import Flask, render_template, request, redirect, url_for, jsonify
# import requests
# import io

# app = Flask(__name__)

# FASTAPI_URL = "http://localhost:8000"  # Fixed: removed /docs

# @app.route('/')
# def home():
#     return render_template('index.html')

# @app.route('/upload', methods=['POST'])
# def upload():
#     # Get the file from the request
#     file = request.files.get('file')
#     instruction = request.form.get('instruction', '')  # Get instruction field
    
#     if not file:
#         return jsonify({"error": "No file uploaded"}), 400
    
#     if not instruction:
#         return jsonify({"error": "No instruction provided"}), 400
    
#     try:
#         # Read file content into memory to allow multiple reads
#         file_content = file.read()
#         file.seek(0)  # Reset file pointer
        
#         # Prepare multipart form data for FastAPI
#         files = {
#             'file': (file.filename, io.BytesIO(file_content), file.mimetype or 'image/jpeg')
#         }
#         data = {
#             'instruction': instruction
#         }
        
#         # Send to FastAPI backend
#         resp = requests.post(
#             f"{FASTAPI_URL}/process-bill",
#             files=files,
#             data=data,
#             timeout=60
#         )
        
#         # Check response status
#         if resp.status_code == 200:
#             data = resp.json()
#             bill_id = data.get("bill_id")
            
#             if not bill_id:
#                 return jsonify({"error": "Error: Could not get bill ID"}), 500
            
#             return redirect(url_for('progress', bill_id=bill_id))
#         else:
#             error_detail = resp.json() if resp.headers.get('Content-Type') == 'application/json' else resp.text
#             return jsonify({"error": f"Backend error: {error_detail}"}), resp.status_code
    
#     except requests.exceptions.ConnectionError:
#         return jsonify({"error": "Cannot connect to backend. Is FastAPI running on port 8000?"}), 503
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "Request timeout. Please try again."}), 504
#     except Exception as e:
#         return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# @app.route('/progress/<bill_id>')
# def progress(bill_id):
#     return render_template('progress.html', bill_id=bill_id)

# @app.route('/progress/status/<bill_id>')
# def get_status(bill_id):
#     """Simulated message polling from RabbitMQ or FastAPI"""
#     # In reality, you'd use a RabbitMQ consumer or WebSocket endpoint
#     # Here we just mimic queued messages for demo
#     sample_messages = [
#         "Bill uploaded",
#         "Extracting items...",
#         "Analyzing participants...",
#         "Splitting costs...",
#         "Finalizing results...",
#         "Process completed ✅"
#     ]
    
#     return jsonify(sample_messages)

# @app.route('/result/<bill_id>')
# def result(bill_id):
#     try:
#         resp = requests.get(f"{FASTAPI_URL}/bill/{bill_id}", timeout=10)
        
#         if resp.status_code != 200:
#             return f"Error fetching bill details: {resp.status_code}", 500
        
#         bill_data = resp.json()
#         return render_template('result.html', bill_id=bill_id, bill_json=bill_data)
    
#     except Exception as e:
#         return f"Error: {str(e)}", 500

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)



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

"""
Simple test Flask app to debug the issue
"""

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Server</title>
    </head>
    <body>
        <h1>🎉 Flask Server is Working!</h1>
        <p>The server is running successfully on port 5000.</p>
        <p><a href="/test">Test Page</a></p>
    </body>
    </html>
    '''

@app.route('/test')
def test():
    return {'status': 'success', 'message': 'API is working'}

if __name__ == '__main__':
    print("🚀 Starting Test Flask Server")
    print("📡 Server will run at: http://localhost:5000")
    print("=" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

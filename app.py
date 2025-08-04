"""
Flask Web Application for Real-time ERP Integration with Playwright
==================================================================

This Flask app serves your attendance portal and provides real-time
data fetching from the Geethanjali ERP system using Playwright automation.

Features:
- Playwright browser automation
- Single roll number authentication
- Real-time ERP data extraction
- RESTful API for frontend
- Session management
- Error handling
"""

from flask import Flask, render_template, request, jsonify, session
import asyncio
import os
import json
from datetime import datetime
import logging
from playwright_erp_scraper import scrape_student_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

@app.route('/')
def index():
    """Serve the main attendance portal"""
    return render_template('index.html')

@app.route('/api/fetch-student-data', methods=['POST'])
def api_fetch_student_data():
    """
    API endpoint to fetch student data using roll number only
    """
    try:
        data = request.get_json()
        roll_number = data.get('rollNumber', '').strip()
        
        if not roll_number:
            return jsonify({
                'success': False,
                'error': 'Roll number is required'
            }), 400
        
        logger.info(f"Fetching data for roll number: {roll_number}")
        
        # Use asyncio to run the Playwright scraper
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(scrape_student_data(roll_number))
            
            if result['success']:
                # Process the data for frontend
                processed_data = process_student_data(result)
                
                # Store in session for caching
                session['last_data'] = processed_data
                session['last_roll_number'] = roll_number
                session['last_fetch_time'] = datetime.now().isoformat()
                
                return jsonify({
                    'success': True,
                    'data': processed_data,
                    'message': 'Student data fetched successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to fetch student data')
                }), 400
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error fetching student data: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch student data: {str(e)}'
        }), 500

@app.route('/api/test-erp-connection', methods=['GET'])
def api_test_connection():
    """
    Test ERP connection
    """
    try:
        import requests
        response = requests.get('https://geethanjali-erp.com/GCET/Login.aspx', timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'ERP system is accessible',
                'status_code': response.status_code
            })
        else:
            return jsonify({
                'success': False,
                'message': f'ERP system returned status: {response.status_code}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Cannot connect to ERP system: {str(e)}'
        })

@app.route('/scrape', methods=['POST'])
def scrape_attendance():
    """
    Scrape attendance data for the given roll number
    """
    try:
        data = request.get_json()
        roll_number = data.get('roll_number', '').strip()

        if not roll_number:
            return jsonify({
                'error': 'Roll number is required'
            }), 400

        logger.info(f"Scraping attendance for roll number: {roll_number}")

        # Create new event loop for this request
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Pass roll_number directly to scrape_student_data
            raw_data = loop.run_until_complete(scrape_student_data(roll_number))

            if raw_data and 'attendance' in raw_data:
                logger.info(f"Successfully scraped data for {roll_number}")
                attendance_data = raw_data['attendance']
                
                # Get the grid data to find current semester totals
                grid_data = attendance_data.get('grid_data', [])
                
                # Find the last "Total" row which represents current semester
                current_semester_data = None
                if grid_data:
                    for row in reversed(grid_data):  # Start from the end
                        if len(row) >= 4 and row[0] == 'Total':
                            current_semester_data = row
                            logger.info(f"Found current semester total row: {row}")
                            break
                
                if current_semester_data:
                    total_conducted = int(current_semester_data[1])
                    total_attended = int(current_semester_data[2])
                    current_percentage = float(current_semester_data[3])
                    
                    logger.info(f"Current semester attendance: {total_attended}/{total_conducted} ({current_percentage}%)")
                else:
                    # Fallback to overall data if no current semester found
                    total_conducted = attendance_data.get('total_classes_conducted', 0)
                    total_attended = attendance_data.get('total_classes_attended', 0)
                    current_percentage = attendance_data.get('overall_percentage', 0)
                    
                    logger.info(f"Using overall attendance: {total_attended}/{total_conducted} ({current_percentage}%)")
                
                # Create a single current semester attendance record
                current_subject = {
                    'name': 'Current Semester Attendance',
                    'present': str(total_attended),
                    'total': str(total_conducted),
                    'absent': str(total_conducted - total_attended),
                    'percentage': f"{current_percentage:.2f}"
                }
                
                return jsonify({
                    'success': True,
                    'subjects': [current_subject]
                })
            else:
                logger.warning(f"No attendance data found for roll number: {roll_number}")
                return jsonify({
                    'success': False,
                    'error': 'No attendance data found. Please check your roll number.'
                }), 404

        except Exception as e:
            logger.error(f"Scraping error for {roll_number}: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to fetch attendance data: {str(e)}'
            }), 500

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

def process_student_data(raw_data):
    """
    Process raw ERP data for frontend consumption
    """
    try:
        student_info = raw_data.get('student_info', {})
        attendance_data = raw_data.get('attendance', {})
        marks_data = raw_data.get('marks', {})
        
        # Extract basic student information
        name = student_info.get('name', 'Unknown Student')
        roll_number = student_info.get('roll_number', raw_data.get('roll_number', 'Unknown'))
        branch = student_info.get('branch', 'Unknown')
        year = student_info.get('year', 'Unknown')
        semester = student_info.get('semester', 'Unknown')
        
        # Process attendance data
        attendance_info = process_attendance_info(attendance_data)
        
        # Process marks data
        marks_info = process_marks_info(marks_data)
        
        return {
            'name': name,
            'rollNumber': roll_number,
            'branch': branch,
            'year': year,
            'semester': semester,
            'attendance': attendance_info,
            'marks': marks_info,
            'lastUpdated': raw_data.get('extracted_at', datetime.now().isoformat()),
            'source': 'Live ERP Data (Playwright)',
            'pageUrl': raw_data.get('page_url', ''),
            'rawData': raw_data  # Include raw data for debugging
        }
        
    except Exception as e:
        logger.error(f"Error processing student data: {e}")
        return {
            'error': f'Failed to process data: {str(e)}',
            'rawData': raw_data
        }

def process_attendance_info(attendance_data):
    """Process attendance data"""
    try:
        if not attendance_data:
            return {
                'available': False,
                'message': 'No attendance data found'
            }

        # Check for table data - support both grid_data and table_data
        table_data = attendance_data.get('grid_data', attendance_data.get('table_data', []))

        # Extract metrics
        total_classes = attendance_data.get('total_classes_conducted', attendance_data.get('total_classes', 'N/A'))
        attended_classes = attendance_data.get('total_classes_attended', attendance_data.get('attended_classes', 'N/A'))
        percentage = attendance_data.get('overall_percentage', attendance_data.get('percentage', 'N/A'))

        # Process table data if available
        subjects = []
        if table_data and len(table_data) > 1:  # Skip header row
            headers = table_data[0] if table_data else []
            logger.info(f"Processing attendance table with headers: {headers}")

            for row in table_data[1:]:
                if len(row) >= 5 and row[0] != 'Total':  # Skip total rows and ensure all required fields are present
                    try:
                        total_classes_row = int(row[2])
                        attended_classes_row = int(row[3])
                        absent_classes = total_classes_row - attended_classes_row
                        percentage_row = float(row[4])
                        
                        subject_info = {
                            'name': f"{row[0]} ({row[1]})",  # Month and Semester
                            'present': str(attended_classes_row),
                            'total': str(total_classes_row),
                            'absent': str(absent_classes),
                            'percentage': f"{percentage_row:.2f}"
                        }
                        subjects.append(subject_info)
                        logger.info(f"Added subject: {subject_info['name']} - {subject_info['present']}/{subject_info['total']} ({subject_info['percentage']}%)")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Skipping invalid row: {row} - Error: {e}")
                        continue

        logger.info(f"Processed {len(subjects)} attendance records")
        return {
            'available': True,
            'summary': {
                'totalClasses': total_classes,
                'attendedClasses': attended_classes,
                'percentage': percentage
            },
            'subjects': subjects,
            'tableData': table_data,
            'raw': attendance_data
        }

    except Exception as e:
        logger.error(f"Error processing attendance: {e}")
        return {
            'available': False,
            'error': str(e),
            'raw': attendance_data
        }

def process_marks_info(marks_data):
    """Process marks/grades data"""
    try:
        if not marks_data:
            return {
                'available': False,
                'message': 'No marks data found'
            }
        
        # Check for table data
        table_data = marks_data.get('table_data', [])
        
        # Process table data if available
        subjects = []
        if table_data and len(table_data) > 1:  # Skip header row
            headers = table_data[0] if table_data else []
            
            for row in table_data[1:]:
                if len(row) >= 2:  # At least subject and some data
                    subject_info = {
                        'name': row[0] if len(row) > 0 else 'Unknown',
                        'marks': row[1:] if len(row) > 1 else []
                    }
                    subjects.append(subject_info)
        
        return {
            'available': True,
            'subjects': subjects,
            'tableData': table_data,
            'raw': marks_data
        }
        
    except Exception as e:
        logger.error(f"Error processing marks: {e}")
        return {
            'available': False,
            'error': str(e),
            'raw': marks_data
        }

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """
    Clear session data
    """
    session.clear()
    
    return jsonify({
        'success': True,
        'message': 'Session cleared successfully'
    })

@app.route('/api/get-cached-data', methods=['GET'])
def api_get_cached_data():
    """
    Get cached student data from session
    """
    if 'last_data' in session:
        return jsonify({
            'success': True,
            'data': session['last_data'],
            'rollNumber': session.get('last_roll_number'),
            'fetchTime': session.get('last_fetch_time'),
            'cached': True
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No cached data available'
        }), 404

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    print("🚀 Starting Playwright ERP Integration Server")
    print("=" * 50)
    print("📡 Server will run at: http://localhost:5000")
    print("🤖 Using Playwright for browser automation")
    print("🎯 Single roll number authentication system")
    print("=" * 50)
    
    # Start the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)

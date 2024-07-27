from flask import Flask, request, jsonify
import google.generativeai as genai
import sqlite3
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

genai.configure(api_key='AIzaSyAO2ohK36Fc-DV_Ryi1q1CU-aFxQmoA0tw')

DATABASE = 'custom_options.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS custom_options
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     url TEXT UNIQUE, 
                     options TEXT)''')
    conn.commit()
    conn.close()

def load_custom_options(url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT options FROM custom_options WHERE url = ?', (url,))
    result = cursor.fetchone()
    conn.close()
    if result:
        options =json.loads(result[0])
        return {opt['label']: opt['prompt'] for opt in options}
    return {}

def save_custom_option(label, prompt, url):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT options FROM custom_options WHERE url = ?', (url,))
        row = cursor.fetchone()
        if row:
            options = json.loads(row[0])
            options.append({'label': label, 'prompt': prompt})
            cursor.execute('UPDATE custom_options SET options = ? WHERE url = ?', 
                           (json.dumps(options), url))
        else:
            options = [{'label': label, 'prompt': prompt}]
            cursor.execute('INSERT INTO custom_options (url, options) VALUES (?, ?)', 
                           (url, json.dumps(options)))
        conn.commit()
    except Exception as e:
        print(f"Error in save_custom_option: {str(e)}")  # Add this line for debugging
        conn.rollback()
        raise
    finally:
        conn.close()

def remove_custom_option(label, url):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT options FROM custom_options WHERE url = ?', (url,))
    row = cursor.fetchone()
    if row:
        options = json.loads(row[0])
        options = [opt for opt in options if opt['label'] != label]
        cursor.execute('UPDATE custom_options SET options = ? WHERE url = ?', 
                       (json.dumps(options), url))
        conn.commit()
    conn.close()

def generate_comment(post_content, style, custom_prompt=None):
    if custom_prompt:
        prompt = f"{custom_prompt}: {post_content}"
    elif style == "neutral":
        prompt = f"Be a calm and composed LinkedIn business coach. Respond to this LinkedIn post with a comment that conveys a neutral perspective. Make sure not to repeat what has already been said in the post. Use new words, phrases, ideas and insights. Do not include any hashtags and emoji. Keep it less than 15 words: {post_content}"
    elif style == "new insight":
        prompt = f"The above is a post on LinkedIn. I want to be an authoritative and insightful LinkedIn user who is friendly in response to the post. Write and add brand new insights in response to the post and make sure not to repeat what has already been said in the post. Use new words, phrases, ideas and insights. Keep it short and professional: {post_content}"
    else:
        prompt = f"Write a {style} comment about this LinkedIn post: {post_content}"

    try:
        response = genai.generate_text(prompt=prompt, temperature=0.7)
        if hasattr(response, 'candidates'):
            candidates = response.candidates
            if candidates:
                first_candidate = candidates[0]
                output_text = first_candidate.get('output', "Error: No output found in the API response.")
            else:
                output_text = "Error: No output from the API."
        else:
            output_text = "Error: No candidates found in the API response."
    except Exception as e:
        output_text = f"Error generating comment: {str(e)}"

    return output_text

@app.route('/generate_comment', methods=['POST'])
def generate_comment_endpoint():
    try:
        data = request.json
        post_content = data.get('postContent', '')
        style = data.get('style', '')
        url = data.get('url', '')
        custom_options = load_custom_options(url)

        if post_content and style:
            if style in custom_options:
                custom_prompt = custom_options[style]
                generated_comment = generate_comment(post_content, style, custom_prompt=custom_prompt)
            else:
                generated_comment = generate_comment(post_content, style)
            return jsonify({'generated_comment': generated_comment})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/add_custom_option', methods=['POST'])
def add_custom_option():
    try:
        data = request.json
        label = data.get('label', '')
        prompt = data.get('prompt', '')
        url = data.get('url', '')
        if label and prompt and url:
            save_custom_option(label, prompt, url)
            return jsonify({'message': 'Custom option added successfully'})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        # print(f"Error in add_custom_option: {str(e)}")  # Add this line for debugging
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/get_custom_options', methods=['GET'])
def get_custom_options():
    try:
        url = request.args.get('url', '')
        if not url:
            return jsonify({'error': 'URL parameter is required'}), 400
        
        options = load_custom_options(url)
        
        # If no options found for this URL, return an empty object
        if not options:
            return jsonify({})
        
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/remove_custom_option', methods=['POST'])
def remove_custom_option_endpoint():
    try:
        data = request.json
        url = data.get('url', '')
        label = data.get('label', '')
        if url and label:
            remove_custom_option(label, url)
            return jsonify({'message': 'Custom option removed successfully'})
        else:
            return jsonify({'error': 'Invalid input'}), 400
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
@app.route('/save_url', methods=['POST'])
def save_url():
    try:
        data = request.json
        url = data.get('url', '').strip()
        if url:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM custom_options WHERE url = ?', (url,))
            existing_url = cursor.fetchone()
            
            if existing_url:
                return jsonify({'message': 'URL already exists', 'url': url}), 200
            
            cursor.execute('INSERT INTO custom_options (url, options) VALUES (?, ?)', 
                           (url, json.dumps([])))
            conn.commit()
            conn.close()
            print(f"URL '{url}' stored successfully with empty options array.")
            return jsonify({'message': 'URL saved successfully', 'url': url})
        else:
            return jsonify({'error': 'URL not provided'}), 400
    except sqlite3.IntegrityError:
        return jsonify({'message': 'URL already exists', 'url': url}), 200
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)


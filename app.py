from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Database connection
def get_db():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME', 'railway'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', 5432)
    )

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'tool4-ai-readiness'})

@app.route('/api/assess', methods=['POST'])
def assess_readiness():
    """
    Receives assessment answers, calculates score, stores in database
    """
    data = request.json
    
    # Extract data
    company_name = data.get('company_name', 'Anonymous')
    industry = data.get('industry')
    email = data.get('email')
    answers = data.get('answers')  # Dict of question_num: value
    
    if not answers:
        return jsonify({'error': 'No answers provided'}), 400
    
    # Calculate overall score
    values = list(answers.values())
    overall_score = round(sum(values) / len(values))
    
    # Calculate category scores
    categories = {
        'Data Infrastructure': [1],
        'Process Maturity': [2],
        'Team Readiness': [3],
        'Financial Capacity': [4],
        'Problem Definition': [5],
        'Technical Foundation': [6],
        'Decision Authority': [7]
    }
    
    category_scores = {}
    for category, question_nums in categories.items():
        category_values = [answers.get(str(q), 0) for q in question_nums]
        category_scores[category] = round(sum(category_values) / len(category_values))
    
    # Determine readiness level
    if overall_score >= 80:
        level = "Highly Ready for AI"
        description = "Your business has excellent foundations for AI implementation. You're positioned to see significant ROI quickly."
        recommendation = "You're in the top 15% of businesses we've analyzed. Let's build something powerful together."
        next_steps = [
            "Schedule discovery call to identify specific automation opportunities",
            "Review your tech stack for integration points",
            "Create detailed implementation roadmap with ROI projections"
        ]
    elif overall_score >= 60:
        level = "Ready with Some Preparation"
        description = "You have solid foundations but a few gaps to address. With targeted preparation, AI can transform your operations."
        recommendation = "You're in good shape. Let's identify the quick wins and create a roadmap for the rest."
        next_steps = [
            "Address gaps in low-scoring categories",
            "Start with one high-impact automation project",
            "Build internal processes to support AI adoption"
        ]
    elif overall_score >= 40:
        level = "Moderate Readiness"
        description = "You have potential but need foundational work before AI implementation. The good news: we know exactly what to fix."
        recommendation = "AI can still help you, but let's start with the basics. We'll show you the path forward."
        next_steps = [
            "Focus on data organization and process documentation",
            "Invest in team training and change management",
            "Consider starting with simple automation before full AI"
        ]
    else:
        level = "Early Stage"
        description = "You're in the exploration phase. AI is possible but requires significant groundwork first."
        recommendation = "No problem - everyone starts somewhere. Let's talk about what low-hanging fruit makes sense for you now."
        next_steps = [
            "Document existing workflows and pain points",
            "Digitize manual processes",
            "Build team comfort with basic automation tools"
        ]
    
    # Identify weakest areas
    weak_categories = sorted(category_scores.items(), key=lambda x: x[1])[:3]
    
    # Store in database
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Insert assessment
    cur.execute("""
        INSERT INTO readiness_assessments (
            company_name, industry, email, answers, 
            overall_score, category_scores, readiness_level, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
    """, (
        company_name,
        industry,
        email,
        json.dumps(answers),
        overall_score,
        json.dumps(category_scores),
        level
    ))
    
    assessment_id = cur.fetchone()['id']
    
    # CIP: Log patterns
    if industry and overall_score:
        cur.execute("""
            INSERT INTO readiness_patterns (pattern_type, pattern_data, frequency, avg_score, last_updated)
            VALUES ('industry_readiness', %s, 1, %s, NOW())
            ON CONFLICT (pattern_type, pattern_data)
            DO UPDATE SET 
                frequency = readiness_patterns.frequency + 1,
                avg_score = (readiness_patterns.avg_score * readiness_patterns.frequency + EXCLUDED.avg_score) / (readiness_patterns.frequency + 1),
                last_updated = NOW()
        """, (json.dumps({'industry': industry}), overall_score))
    
    # Log weak category patterns
    for category, score in weak_categories:
        cur.execute("""
            INSERT INTO readiness_patterns (pattern_type, pattern_data, frequency, avg_score, last_updated)
            VALUES ('weak_category', %s, 1, %s, NOW())
            ON CONFLICT (pattern_type, pattern_data)
            DO UPDATE SET 
                frequency = readiness_patterns.frequency + 1,
                avg_score = (readiness_patterns.avg_score * readiness_patterns.frequency + EXCLUDED.avg_score) / (readiness_patterns.frequency + 1),
                last_updated = NOW()
        """, (json.dumps({'category': category}), score))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({
        'assessment_id': assessment_id,
        'overall_score': overall_score,
        'category_scores': category_scores,
        'readiness_level': level,
        'description': description,
        'recommendation': recommendation,
        'next_steps': next_steps,
        'weak_areas': [cat for cat, score in weak_categories]
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get aggregate statistics for gamification
    (e.g., "You're in top 20% of businesses")
    """
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get total assessments
    cur.execute("SELECT COUNT(*) as total FROM readiness_assessments")
    total = cur.fetchone()['total']
    
    # Get average score
    cur.execute("SELECT AVG(overall_score) as avg_score FROM readiness_assessments")
    avg_score_result = cur.fetchone()
    avg_score = round(float(avg_score_result['avg_score'])) if avg_score_result['avg_score'] else 0
    
    # Get industry breakdown
    cur.execute("""
        SELECT industry, AVG(overall_score) as avg_score, COUNT(*) as count
        FROM readiness_assessments
        WHERE industry IS NOT NULL
        GROUP BY industry
        ORDER BY count DESC
        LIMIT 5
    """)
    top_industries = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'total_assessments': int(total),
        'average_score': avg_score,
        'top_industries': [
            {
                'industry': row['industry'],
                'avg_score': round(float(row['avg_score'])),
                'count': int(row['count'])
            }
            for row in top_industries
        ]
    })

@app.route('/api/percentile/<int:score>', methods=['GET'])
def get_percentile(score):
    """
    Calculate what percentile this score is in
    (for gamification: "You're in top X% of businesses")
    """
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) as count
        FROM readiness_assessments
        WHERE overall_score < %s
    """, (score,))
    
    lower_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) as total FROM readiness_assessments")
    total = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    if total == 0:
        percentile = 50
    else:
        percentile = round((lower_count / total) * 100)
    
    return jsonify({
        'percentile': percentile,
        'message': f"You're in the top {100 - percentile}% of businesses we've analyzed"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
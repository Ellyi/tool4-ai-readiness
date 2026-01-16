"""
CIP Engine for Tool #4 - AI Readiness Scanner
Makes Tool #4 LEARN from usage and generate market intelligence
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

class CIPEngineReadiness:
    """
    Learning system that:
    1. Logs patterns from each readiness assessment
    2. Analyzes trends across all assessments
    3. Generates market intelligence reports
    4. Identifies which businesses convert to Nuru
    """
    
    def __init__(self):
        self.conn = self._get_connection()
    
    def _get_connection(self):
        # Parse DATABASE_URL from Railway
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        else:
            # Fallback for local dev
            return psycopg2.connect(
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME', 'railway'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD'),
                port=os.getenv('DB_PORT', 5432),
                cursor_factory=RealDictCursor
            )
    
    def log_patterns(self, assessment_data):
        """
        Called after each assessment to log patterns
        Runs automatically every time someone completes assessment
        """
        cur = self.conn.cursor()
        
        # Extract data
        industry = assessment_data.get('industry')
        overall_score = assessment_data.get('overall_score')
        category_scores = assessment_data.get('category_scores')
        
        # Log industry readiness patterns
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
        
        # Log blocking factors (categories with low scores)
        if category_scores:
            for category, score in category_scores.items():
                if score < 60:  # Blocking threshold
                    cur.execute("""
                        INSERT INTO readiness_patterns (pattern_type, pattern_data, frequency, avg_score, last_updated)
                        VALUES ('blocking_factor', %s, 1, %s, NOW())
                        ON CONFLICT (pattern_type, pattern_data)
                        DO UPDATE SET 
                            frequency = readiness_patterns.frequency + 1,
                            avg_score = (readiness_patterns.avg_score * readiness_patterns.frequency + EXCLUDED.avg_score) / (readiness_patterns.frequency + 1),
                            last_updated = NOW()
                    """, (json.dumps({'category': category}), score))
        
        # Log high performers (for conversion prediction)
        if overall_score >= 75:
            cur.execute("""
                INSERT INTO readiness_patterns (pattern_type, pattern_data, frequency, last_updated)
                VALUES ('high_performer', %s, 1, NOW())
                ON CONFLICT (pattern_type, pattern_data)
                DO UPDATE SET 
                    frequency = readiness_patterns.frequency + 1,
                    last_updated = NOW()
            """, (json.dumps({'score_range': '75+', 'industry': industry}),))
        
        self.conn.commit()
        cur.close()
        
        # Check if we should run analysis (every 10 assessments)
        self._check_analysis_trigger()
    
    def _check_analysis_trigger(self):
        """
        Runs pattern analysis every 10 assessments
        """
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM readiness_assessments")
        count = cur.fetchone()['count']
        cur.close()
        
        if count % 10 == 0:
            self.analyze_patterns()
    
    def analyze_patterns(self):
        """
        Analyzes accumulated assessment data
        Generates insights about market trends
        """
        cur = self.conn.cursor()
        
        # Find industries with highest readiness
        cur.execute("""
            SELECT 
                rp.pattern_data->>'industry' as industry,
                rp.avg_score,
                rp.frequency
            FROM readiness_patterns rp
            WHERE rp.pattern_type = 'industry_readiness'
            AND rp.frequency >= 3
            ORDER BY rp.avg_score DESC
            LIMIT 5
        """)
        top_industries = cur.fetchall()
        
        # Find most common blocking factors
        cur.execute("""
            SELECT 
                rp.pattern_data->>'category' as category,
                rp.frequency,
                rp.avg_score
            FROM readiness_patterns rp
            WHERE rp.pattern_type = 'blocking_factor'
            ORDER BY rp.frequency DESC
            LIMIT 5
        """)
        blocking_factors = cur.fetchall()
        
        # Calculate high performer conversion potential
        cur.execute("""
            SELECT COUNT(*) as high_performers
            FROM readiness_assessments
            WHERE overall_score >= 75
        """)
        high_performers = cur.fetchone()['high_performers']
        
        cur.execute("SELECT COUNT(*) as total FROM readiness_assessments")
        total = cur.fetchone()['total']
        
        # Generate insights
        if top_industries:
            top_industry = top_industries[0]
            insight = f"Industry with highest AI readiness: {top_industry['industry']} (avg {float(top_industry['avg_score']):.1f} from {top_industry['frequency']} assessments)"
            
            cur.execute("""
                INSERT INTO readiness_insights (
                    insight_type, insight_text, confidence, supporting_data, generated_at
                ) VALUES (%s, %s, %s, %s, NOW())
            """, (
                'top_ready_industry',
                insight,
                0.90,
                json.dumps({
                    'industry': top_industry['industry'],
                    'avg_score': float(top_industry['avg_score']),
                    'sample_size': int(top_industry['frequency'])
                })
            ))
        
        if blocking_factors:
            top_blocker = blocking_factors[0]
            insight = f"Most common readiness blocker: {top_blocker['category']} ({top_blocker['frequency']} businesses struggle here, avg {float(top_blocker['avg_score']):.1f})"
            
            cur.execute("""
                INSERT INTO readiness_insights (
                    insight_type, insight_text, confidence, supporting_data, generated_at
                ) VALUES (%s, %s, %s, %s, NOW())
            """, (
                'top_blocker',
                insight,
                0.95,
                json.dumps({
                    'category': top_blocker['category'],
                    'frequency': int(top_blocker['frequency']),
                    'avg_score': float(top_blocker['avg_score'])
                })
            ))
        
        # Conversion prediction insight
        if total > 0:
            conversion_rate = (high_performers / total) * 100
            insight = f"High-readiness businesses (75+ score): {high_performers} of {total} ({conversion_rate:.1f}%) - prime targets for Nuru conversion"
            
            cur.execute("""
                INSERT INTO readiness_insights (
                    insight_type, insight_text, confidence, supporting_data, generated_at
                ) VALUES (%s, %s, %s, %s, NOW())
            """, (
                'conversion_potential',
                insight,
                0.85,
                json.dumps({
                    'high_performers': int(high_performers),
                    'total': int(total),
                    'conversion_rate': float(conversion_rate)
                })
            ))
        
        self.conn.commit()
        cur.close()
    
    def generate_monthly_report(self):
        """
        Generates comprehensive intelligence report for Eli
        Shows what we learned from all assessments
        """
        cur = self.conn.cursor()
        
        # Total assessments
        cur.execute("SELECT COUNT(*) as total FROM readiness_assessments")
        total_assessments = cur.fetchone()['total']
        
        # Average readiness score
        cur.execute("SELECT AVG(overall_score) as avg_score FROM readiness_assessments")
        avg_score_result = cur.fetchone()
        avg_score = float(avg_score_result['avg_score']) if avg_score_result['avg_score'] else 0
        
        # Top ready industries
        cur.execute("""
            SELECT 
                rp.pattern_data->>'industry' as industry,
                rp.avg_score,
                rp.frequency
            FROM readiness_patterns rp
            WHERE rp.pattern_type = 'industry_readiness'
            AND rp.frequency >= 3
            ORDER BY rp.avg_score DESC
            LIMIT 5
        """)
        top_industries = cur.fetchall()
        
        # Blocking factors
        cur.execute("""
            SELECT 
                rp.pattern_data->>'category' as category,
                rp.frequency,
                rp.avg_score
            FROM readiness_patterns rp
            WHERE rp.pattern_type = 'blocking_factor'
            ORDER BY rp.frequency DESC
            LIMIT 5
        """)
        blocking_factors = cur.fetchall()
        
        # Conversion opportunities (high scorers)
        cur.execute("""
            SELECT COUNT(*) as count, AVG(overall_score) as avg_score
            FROM readiness_assessments
            WHERE overall_score >= 75
        """)
        high_ready = cur.fetchone()
        
        # Market opportunities
        opportunities = []
        for industry in top_industries[:3]:
            if industry['frequency'] >= 5:
                opportunities.append({
                    'opportunity': f"Target {industry['industry']} - high AI readiness",
                    'market_size': int(industry['frequency']),
                    'avg_readiness': float(industry['avg_score']),
                    'potential_conversions': int(industry['frequency']) * 0.52  # 52% conversion estimate
                })
        
        # Recent insights
        cur.execute("""
            SELECT insight_type, insight_text, confidence, supporting_data
            FROM readiness_insights
            WHERE generated_at >= NOW() - INTERVAL '30 days'
            ORDER BY confidence DESC, generated_at DESC
            LIMIT 5
        """)
        recent_insights = cur.fetchall()
        
        cur.close()
        
        return {
            'period': 'Last 30 days',
            'total_assessments': int(total_assessments),
            'avg_readiness_score': avg_score,
            'top_ready_industries': [
                {
                    'industry': i['industry'],
                    'avg_score': float(i['avg_score']),
                    'count': int(i['frequency'])
                }
                for i in top_industries
            ],
            'blocking_factors': [
                {
                    'category': b['category'],
                    'frequency': int(b['frequency']),
                    'avg_score': float(b['avg_score'])
                }
                for b in blocking_factors
            ],
            'high_ready_businesses': {
                'count': int(high_ready['count']) if high_ready['count'] else 0,
                'avg_score': float(high_ready['avg_score']) if high_ready['avg_score'] else 0
            },
            'market_opportunities': opportunities,
            'insights': [
                {
                    'type': i['insight_type'],
                    'text': i['insight_text'],
                    'confidence': float(i['confidence'])
                }
                for i in recent_insights
            ],
            'recommendations': self._generate_recommendations(opportunities, blocking_factors)
        }
    
    def _generate_recommendations(self, opportunities, blockers):
        """
        Generates actionable recommendations based on patterns
        """
        recommendations = []
        
        if opportunities:
            top_opp = opportunities[0]
            recommendations.append(
                f"TARGET: {top_opp['opportunity']} - {int(top_opp['potential_conversions'])} potential Nuru conversions"
            )
        
        if blockers:
            top_blocker = blockers[0]
            recommendations.append(
                f"BUILD: {top_blocker['category']} support template - {top_blocker['frequency']} businesses need help here"
            )
        
        return recommendations
    
    def close(self):
        if self.conn:
            self.conn.close()
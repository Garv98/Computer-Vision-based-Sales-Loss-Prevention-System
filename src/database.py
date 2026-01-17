import psycopg2 
from psycopg2.extras import DictCursor, execute_values
from datetime import datetime
import uuid
import requests
import json

# Ollama Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:latest"  # Change to your installed model (mistral, llama3.2, etc.)
conn = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="your_password",
    dbname="salesloss"
)

class DataBaseOrm:
    def __init__(self):
        self.conn = psycopg2.connect(
                    host="localhost",
                    user="postgres",
                    password="your_password",
                    dbname="salesloss"
                )
        self.cursor = self.conn.cursor(cursor_factory= DictCursor)
        # Ensure indexes exist for performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better query performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_bounding_box_coords ON bounding_box ((x1 + x2), (y1 + y2))",
            "CREATE INDEX IF NOT EXISTS idx_bounding_box_shard ON bounding_box (video_shard)",
            "CREATE INDEX IF NOT EXISTS idx_bounding_box_tracking ON bounding_box (tracking_id, video_shard)",
            "CREATE INDEX IF NOT EXISTS idx_tracking_time ON tracking (time)",
            "CREATE INDEX IF NOT EXISTS idx_tracking_shard ON tracking (video_shard)",
            "CREATE INDEX IF NOT EXISTS idx_tracking_cam ON tracking (cam_id)",
            "CREATE INDEX IF NOT EXISTS idx_region_cam ON region_defined (cam_id)",
        ]
        try:
            for idx_sql in indexes:
                self.cursor.execute(idx_sql)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Index creation skipped (may already exist): {e}")

    def add_camera(self, camera_id, cam_name):
        try:
            query = "INSERT INTO camera (cam_name, cam_id, status) VALUES (%s, %s, 'ENABLED')"
            self.cursor.execute(query, (cam_name, camera_id))
            self.conn.commit()
            print(f"Camera {camera_id} added.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding camera: {e}")

    def get_camera(self, camera_id):
        query = "SELECT * FROM camera WHERE cam_id = %s"
        self.cursor.execute(query, (camera_id,))
        return self.cursor.fetchone()

    def get_all_cameras(self):
        query = "SELECT * FROM camera"
        self.cursor.execute(query)
        # Convert DictRows to real dicts to ensure JSON serialization uses keys
        return [dict(row) for row in self.cursor.fetchall()]

    def update_camera(self, current_camera_id, new_camera_name, camera_status):
        try:
            query = """
                    UPDATE camera
                    SET cam_name = %s,
                        status = %s
                    WHERE cam_id = %s
                    """
            self.cursor.execute(query, (new_camera_name, camera_status, current_camera_id))
            self.conn.commit()
            print(f"Camera {current_camera_id} updated.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating camera: {e}")

    def delete_camera(self, camera_id):
        try:
            query = "DELETE FROM camera WHERE cam_id = %s"
            self.cursor.execute(query, (camera_id,))
            self.conn.commit()
            print(f"Camera {camera_id} deleted.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting camera: {e}")

    # --- Tracking CRUD ---
    def add_tracking(self, tracking_id, confusion_time, tracker_group, cam_id, time, video_shard, gender='Unknown'):
        try:
            query = """
                INSERT INTO tracking (tracking_id, confusion_time, tracker_group, cam_id, "time", video_shard, gender)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (tracking_id, confusion_time, tracker_group, cam_id, time, video_shard, gender))
            self.conn.commit()
            print(f"Tracking {tracking_id} added.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding tracking: {e}")

    def batch_insert_tracking(self, tracking_data):
        """
        Batch insert tracking data.
        tracking_data: list of tuples (tracking_id, confusion_time, tracker_group, cam_id, time, video_shard, gender)
        """
        try:
            query = """
                INSERT INTO tracking (tracking_id, confusion_time, tracker_group, cam_id, "time", video_shard, gender)
                VALUES %s
                ON CONFLICT (tracking_id, video_shard) DO NOTHING
            """
            execute_values(self.cursor, query, tracking_data)
            self.conn.commit()
            print(f"Batch inserted {len(tracking_data)} tracking records.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error batch inserting tracking: {e}")

    def get_tracking(self, tracking_id, video_shard):
        query = "SELECT * FROM tracking WHERE tracking_id = %s AND video_shard = %s"
        self.cursor.execute(query, (tracking_id, video_shard))
        return self.cursor.fetchone()

    def delete_tracking(self, tracking_id, video_shard):
        try:
            query = "DELETE FROM tracking WHERE tracking_id = %s AND video_shard = %s"
            self.cursor.execute(query, (tracking_id, video_shard))
            self.conn.commit()
            print(f"Tracking {tracking_id} deleted.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting tracking: {e}")

    # --- Bounding Box CRUD ---
    def add_bounding_box(self, x1, x2, y1, y2, timestamp, tracking_id, video_shard, frame):
        try:
            query = """
                INSERT INTO bounding_box (x1, x2, y1, y2, "timestamp", tracking_id, video_shard, frame)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (x1, x2, y1, y2, timestamp, tracking_id, video_shard, frame))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding bounding box: {e}")

    def batch_insert_bounding_boxes(self, bbox_data):
        """
        Batch insert bounding box data.
        bbox_data: list of tuples (x1, x2, y1, y2, timestamp, tracking_id, video_shard, frame)
        """
        try:
            query = """
                INSERT INTO bounding_box (x1, x2, y1, y2, "timestamp", tracking_id, video_shard, frame)
                VALUES %s
            """
            execute_values(self.cursor, query, bbox_data)
            self.conn.commit()
            print(f"Batch inserted {len(bbox_data)} bounding box records.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error batch inserting bounding boxes: {e}")

    def get_bounding_boxes_by_tracking_id(self, tracking_id):
        query = "SELECT * FROM bounding_box WHERE tracking_id = %s"
        self.cursor.execute(query, (tracking_id,))
        return self.cursor.fetchall()

    # --- Region Defined CRUD ---
    def add_region(self, region_id, region_name, x1, x2, y1, y2, cam_id):
        try:
            query = """
                INSERT INTO region_defined (region_id, region_name, x1, x2, y1, y2, cam_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (region_id, region_name, x1, x2, y1, y2, cam_id))
            self.conn.commit()
            print(f"Region {region_id} added.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding region: {e}")

    def get_region(self, region_id):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = "SELECT * FROM region_defined WHERE region_id = %s"
                cur.execute(query, (region_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting region: {e}")
            return None

    def update_region(self, region_id, region_name, x1, x2, y1, y2):
        try:
            query = """
                UPDATE region_defined
                SET region_name = %s, x1 = %s, x2 = %s, y1 = %s, y2 = %s
                WHERE region_id = %s
            """
            self.cursor.execute(query, (region_name, x1, x2, y1, y2, region_id))
            self.conn.commit()
            print(f"Region {region_id} updated.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating region: {e}")

    def delete_region(self, region_id):
        try:
            query = "DELETE FROM region_defined WHERE region_id = %s"
            self.cursor.execute(query, (region_id,))
            self.conn.commit()
            print(f"Region {region_id} deleted.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting region: {e}")

    # --- Alert CRUD ---
    def add_alert(self, alert_id, type, time, region_id):
        try:
            # Ensure alert_id is a proper UUID string
            if isinstance(alert_id, int):
                alert_id = str(uuid.uuid4())
            query = """
                INSERT INTO alert (alert_id, type, "time", region_id)
                VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(query, (alert_id, type, time, region_id))
            self.conn.commit()
            print(f"Alert {alert_id} added.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding alert: {e}")

    def get_alerts_by_region(self, region_id):
        query = "SELECT * FROM alert WHERE region_id = %s"
        self.cursor.execute(query, (region_id,))
        return self.cursor.fetchall()

    # --- Analytics Queries ---
    def get_footfall_by_region(self, region_id):
        """
        Calculate unique footfall in a region per shard.
        Checks if bounding box center is within region coordinates.
        Only counts each tracking_id ONCE per shard (not per frame).
        """
        try:
            # First get region coordinates
            region = self.get_region(region_id)
            if not region:
                return []
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Query to count unique tracking_ids whose bounding box center falls within region
                # Uses DISTINCT to count each person only once, regardless of how many frames
                query = """
                    SELECT video_shard, COUNT(DISTINCT tracking_id) as footfall
                    FROM bounding_box
                    WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                    AND (y1 + y2) / 2 BETWEEN %s AND %s
                    GROUP BY video_shard
                """
                cur.execute(query, (rx1, rx2, ry1, ry2))
                # Return list of tuples (shard_id, count)
                return [(row['video_shard'], row['footfall']) for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting footfall: {e}")
            return []
    
    def get_total_unique_footfall(self, region_id):
        """
        Get total unique visitors to a region across ALL shards.
        This prevents counting the same person multiple times across shards.
        """
        try:
            region = self.get_region(region_id)
            if not region:
                return 0
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Count unique tracking_ids across ALL shards (not per-shard)
                query = """
                    SELECT COUNT(DISTINCT tracking_id) as total_footfall
                    FROM bounding_box
                    WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                    AND (y1 + y2) / 2 BETWEEN %s AND %s
                """
                cur.execute(query, (rx1, rx2, ry1, ry2))
                result = cur.fetchone()
                return result['total_footfall'] if result else 0
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting total footfall: {e}")
            return 0

    def get_time_spent_in_region(self, region_id):
        """
        Calculate average time spent by tracking_ids in a region per shard.
        """
        try:
            region = self.get_region(region_id)
            if not region:
                return []
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Calculate duration for each track in each shard, then average per shard
                query = """
                    WITH TrackDurations AS (
                        SELECT 
                            video_shard,
                            tracking_id,
                            EXTRACT(EPOCH FROM (MAX("timestamp") - MIN("timestamp"))) as duration
                        FROM bounding_box
                        WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                        AND (y1 + y2) / 2 BETWEEN %s AND %s
                        GROUP BY video_shard, tracking_id
                    )
                    SELECT video_shard, AVG(duration) as avg_time
                    FROM TrackDurations
                    GROUP BY video_shard
                """
                cur.execute(query, (rx1, rx2, ry1, ry2))
                return [(row['video_shard'], row['avg_time']) for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting time spent: {e}")
            return []

    def get_all_regions(self):
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = "SELECT * FROM region_defined"
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting all regions: {e}")
            return []

    def get_shards_by_camera(self, cam_id):
        """
        Get all unique video shards for a specific camera, ordered by time.
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT video_shard, MIN("time") as start_time
                    FROM tracking 
                    WHERE cam_id = %s
                    GROUP BY video_shard
                    ORDER BY start_time ASC
                """
                cur.execute(query, (cam_id,))
                return [row['video_shard'] for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting shards: {e}")
            return []

    def get_demographics_stats(self, region_id):
        """
        Get gender distribution for a region.
        """
        try:
            region = self.get_region(region_id)
            if not region:
                return []
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT t.gender, COUNT(DISTINCT t.tracking_id) as count
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                    GROUP BY t.gender
                """
                cur.execute(query, (rx1, rx2, ry1, ry2))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting demographics: {e}")
            return []

    def get_tracking_duration_stats(self, region_id):
        """
        Get average confusion time (tracking duration) stats.
        """
        try:
            region = self.get_region(region_id)
            if not region:
                return []
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                query = """
                    SELECT t.video_shard, AVG(t.confusion_time) as avg_confusion_time
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                    GROUP BY t.video_shard
                """
                cur.execute(query, (rx1, rx2, ry1, ry2))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting tracking stats: {e}")
            return []

    # --- Region Insights CRUD ---
    def add_region_insight(self, insight_id, date, tracking_group_info, total_footfall, region_id=None):
        try:
            # Check if table has region_id column
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'region_insights' AND column_name = 'region_id'
                """)
                has_region_id = cur.fetchone() is not None
            
            if has_region_id and region_id:
                query = """
                    INSERT INTO region_insights (insight_id, "date", tracking_group_info, total_footfall, region_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.cursor.execute(query, (insight_id, date, tracking_group_info, total_footfall, region_id))
            else:
                query = """
                    INSERT INTO region_insights (insight_id, "date", tracking_group_info, total_footfall)
                    VALUES (%s, %s, %s, %s)
                """
                self.cursor.execute(query, (insight_id, date, tracking_group_info, total_footfall))
            self.conn.commit()
            print(f"Insight {insight_id} added.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error adding insight: {e}")

    def reset_database(self):
        """
        Clears all data from tables but keeps the schema.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    TRUNCATE TABLE public.bounding_box, 
                                   public.tracking, 
                                   public.alert, 
                                   public.region_insights, 
                                   public.region_defined, 
                                   public.camera 
                    CASCADE;
                """)
                self.conn.commit()
                print("Database reset successfully.")
        except Exception as e:
            self.conn.rollback()
            print(f"Error resetting database: {e}")
            raise e

    # --- Advanced Analytics Methods ---
    def get_daily_trends(self, region_id=None, days=7):
        """Get daily footfall trends"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if region_id:
                    region = self.get_region(region_id)
                    if not region:
                        return []
                    rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
                    
                    query = """
                        SELECT DATE(t.time) as date, COUNT(DISTINCT t.tracking_id) as footfall
                        FROM tracking t
                        JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                        WHERE DATE(t.time) >= CURRENT_DATE - INTERVAL '%s days'
                        AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                        AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                        GROUP BY DATE(t.time)
                        ORDER BY date DESC
                    """
                    cur.execute(query, (days, rx1, rx2, ry1, ry2))
                else:
                    query = """
                        SELECT DATE(time) as date, COUNT(DISTINCT tracking_id) as footfall
                        FROM tracking
                        WHERE DATE(time) >= CURRENT_DATE - INTERVAL '%s days'
                        GROUP BY DATE(time)
                        ORDER BY date DESC
                    """
                    cur.execute(query, (days,))
                
                return [{"date": str(row['date']), "footfall": row['footfall']} for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting daily trends: {e}")
            return []

    def get_weekly_trends(self, region_id=None, weeks=4):
        """Get weekly footfall trends"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if region_id:
                    region = self.get_region(region_id)
                    if not region:
                        return []
                    rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
                    
                    query = """
                        SELECT DATE_TRUNC('week', t.time) as week, COUNT(DISTINCT t.tracking_id) as footfall
                        FROM tracking t
                        JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                        WHERE DATE(t.time) >= CURRENT_DATE - INTERVAL '%s weeks'
                        AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                        AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                        GROUP BY week
                        ORDER BY week DESC
                    """
                    cur.execute(query, (weeks, rx1, rx2, ry1, ry2))
                else:
                    query = """
                        SELECT DATE_TRUNC('week', time) as week, COUNT(DISTINCT tracking_id) as footfall
                        FROM tracking
                        WHERE DATE(time) >= CURRENT_DATE - INTERVAL '%s weeks'
                        GROUP BY week
                        ORDER BY week DESC
                    """
                    cur.execute(query, (weeks,))
                
                return [{"week": str(row['week']), "footfall": row['footfall']} for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting weekly trends: {e}")
            return []

    def get_monthly_trends(self, region_id=None, months=6):
        """Get monthly footfall trends"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if region_id:
                    region = self.get_region(region_id)
                    if not region:
                        return []
                    rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
                    
                    query = """
                        SELECT DATE_TRUNC('month', t.time) as month, COUNT(DISTINCT t.tracking_id) as footfall
                        FROM tracking t
                        JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                        WHERE DATE(t.time) >= CURRENT_DATE - INTERVAL '%s months'
                        AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                        AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                        GROUP BY month
                        ORDER BY month DESC
                    """
                    cur.execute(query, (months, rx1, rx2, ry1, ry2))
                else:
                    query = """
                        SELECT DATE_TRUNC('month', time) as month, COUNT(DISTINCT tracking_id) as footfall
                        FROM tracking
                        WHERE DATE(time) >= CURRENT_DATE - INTERVAL '%s months'
                        GROUP BY month
                        ORDER BY month DESC
                    """
                    cur.execute(query, (months,))
                
                return [{"month": str(row['month']), "footfall": row['footfall']} for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting monthly trends: {e}")
            return []

    def get_heatmap_data(self, region_id, shard_id=None, resolution=20):
        """Generate heat map data based on bounding box density"""
        try:
            region = self.get_region(region_id)
            if not region:
                return {"grid_size": {"width": resolution, "height": resolution}, "region_bounds": {}, "cells": []}
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            width = max(rx2 - rx1, 1)
            height = max(ry2 - ry1, 1)
            cell_width = max(width / resolution, 1)
            cell_height = max(height / resolution, 1)
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if shard_id:
                    query = """
                        SELECT 
                            LEAST(GREATEST(FLOOR(((x1 + x2) / 2.0 - %s) / %s), 0), %s - 1) as grid_x,
                            LEAST(GREATEST(FLOOR(((y1 + y2) / 2.0 - %s) / %s), 0), %s - 1) as grid_y,
                            COUNT(*) as density
                        FROM bounding_box
                        WHERE video_shard = %s
                        AND (x1 + x2) / 2 BETWEEN %s AND %s
                        AND (y1 + y2) / 2 BETWEEN %s AND %s
                        GROUP BY grid_x, grid_y
                        ORDER BY density DESC
                    """
                    cur.execute(query, (rx1, cell_width, resolution, ry1, cell_height, resolution, shard_id, rx1, rx2, ry1, ry2))
                else:
                    query = """
                        SELECT 
                            LEAST(GREATEST(FLOOR(((x1 + x2) / 2.0 - %s) / %s), 0), %s - 1) as grid_x,
                            LEAST(GREATEST(FLOOR(((y1 + y2) / 2.0 - %s) / %s), 0), %s - 1) as grid_y,
                            COUNT(*) as density
                        FROM bounding_box
                        WHERE (x1 + x2) / 2 BETWEEN %s AND %s
                        AND (y1 + y2) / 2 BETWEEN %s AND %s
                        GROUP BY grid_x, grid_y
                        ORDER BY density DESC
                    """
                    cur.execute(query, (rx1, cell_width, resolution, ry1, cell_height, resolution, rx1, rx2, ry1, ry2))
                
                heatmap_data = [
                    {
                        "x": int(row['grid_x']), 
                        "y": int(row['grid_y']), 
                        "density": int(row['density'])
                    } 
                    for row in cur.fetchall()
                ]
                
                return {
                    "grid_size": {"width": resolution, "height": resolution},
                    "region_bounds": {"x1": int(rx1), "x2": int(rx2), "y1": int(ry1), "y2": int(ry2)},
                    "cells": heatmap_data
                }
        except Exception as e:
            print(f"Error generating heatmap: {e}")
            return {"grid_size": {"width": resolution, "height": resolution}, "region_bounds": {}, "cells": []}

    # ==================== AI REPORT GENERATION ====================
    
    def get_recent_alerts(self, limit=50, region_id=None):
        """Get recent alerts from database"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if region_id:
                    query = """
                        SELECT a.*, r.region_name 
                        FROM alert a
                        LEFT JOIN region_defined r ON a.region_id = r.region_id
                        WHERE a.region_id = %s
                        ORDER BY a.time DESC LIMIT %s
                    """
                    cur.execute(query, (region_id, limit))
                else:
                    query = """
                        SELECT a.*, r.region_name 
                        FROM alert a
                        LEFT JOIN region_defined r ON a.region_id = r.region_id
                        ORDER BY a.time DESC LIMIT %s
                    """
                    cur.execute(query, (limit,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting recent alerts: {e}")
            return []

    def generate_ai_report(self, region_id, period="daily"):
        """Generate AI-powered report for a region"""
        try:
            region = self.get_region(region_id)
            if not region:
                return {"error": "Region not found"}
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Get period-based stats
                if period == "daily":
                    interval = "1 day"
                elif period == "weekly":
                    interval = "7 days"
                else:
                    interval = "30 days"
                
                # Total footfall
                cur.execute("""
                    SELECT COUNT(DISTINCT t.tracking_id) as total_footfall
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE t.time >= NOW() - INTERVAL %s
                    AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                """, (interval, rx1, rx2, ry1, ry2))
                footfall_result = cur.fetchone()
                total_footfall = footfall_result['total_footfall'] if footfall_result else 0
                
                # Average dwell time
                cur.execute("""
                    SELECT AVG(t.confusion_time) as avg_dwell_time
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE t.time >= NOW() - INTERVAL %s
                    AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                """, (interval, rx1, rx2, ry1, ry2))
                dwell_result = cur.fetchone()
                avg_dwell = float(dwell_result['avg_dwell_time']) if dwell_result and dwell_result['avg_dwell_time'] else 0
                
                # Gender distribution
                cur.execute("""
                    SELECT t.gender, COUNT(DISTINCT t.tracking_id) as count
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE t.time >= NOW() - INTERVAL %s
                    AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                    GROUP BY t.gender
                """, (interval, rx1, rx2, ry1, ry2))
                gender_dist = {row['gender']: row['count'] for row in cur.fetchall()}
                
                # Peak hours (if we have hourly data)
                cur.execute("""
                    SELECT EXTRACT(HOUR FROM t.time) as hour, COUNT(DISTINCT t.tracking_id) as count
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    WHERE t.time >= NOW() - INTERVAL %s
                    AND (b.x1 + b.x2) / 2 BETWEEN %s AND %s
                    AND (b.y1 + b.y2) / 2 BETWEEN %s AND %s
                    GROUP BY hour
                    ORDER BY count DESC
                    LIMIT 3
                """, (interval, rx1, rx2, ry1, ry2))
                peak_hours = [{"hour": int(row['hour']), "visitors": row['count']} for row in cur.fetchall()]
                
                # Alert count
                cur.execute("""
                    SELECT COUNT(*) as alert_count
                    FROM alert
                    WHERE region_id = %s AND time >= NOW() - INTERVAL %s
                """, (region_id, interval))
                alert_result = cur.fetchone()
                alert_count = alert_result['alert_count'] if alert_result else 0
                
                # Generate AI insights
                insights = self._generate_insights(
                    total_footfall, avg_dwell, gender_dist, peak_hours, alert_count, period
                )
                
                return {
                    "region_name": region['region_name'],
                    "period": period,
                    "generated_at": datetime.now().isoformat(),
                    "metrics": {
                        "total_footfall": total_footfall,
                        "avg_dwell_time_seconds": round(avg_dwell, 2),
                        "gender_distribution": gender_dist,
                        "peak_hours": peak_hours,
                        "alert_count": alert_count
                    },
                    "ai_insights": insights
                }
        except Exception as e:
            print(f"Error generating AI report: {e}")
            return {"error": str(e)}

    def _generate_insights(self, footfall, avg_dwell, gender_dist, peak_hours, alert_count, period):
        """Generate AI insights using Ollama LLM"""
        
        # Build context for AI
        gender_summary = ", ".join([f"{k}: {v}" for k, v in gender_dist.items()]) if gender_dist else "No data"
        peak_hours_str = ", ".join([f"{h['hour']}:00 ({h['visitors']} visitors)" for h in peak_hours[:5]]) if peak_hours else "No data"
        
        prompt = f"""You are a retail analytics AI assistant helping a shopkeeper understand their store performance.

Analyze this store data and provide actionable insights:

**Store Metrics ({period} report):**
- Total Footfall: {footfall} visitors
- Average Dwell Time: {avg_dwell:.1f} seconds
- Gender Distribution: {gender_summary}
- Peak Hours: {peak_hours_str}
- Dwell-Time Alerts: {alert_count} (triggered when someone stays too long in one area)

**Instructions:**
1. Provide 3-4 key insights about the store performance (use emojis for visual appeal)
2. Provide 3-4 specific, actionable recommendations for the shopkeeper
3. Be concise and business-focused

Respond in this exact JSON format:
{{
  "summary": ["insight1", "insight2", "insight3"],
  "recommendations": ["recommendation1", "recommendation2", "recommendation3"],
  "confidence_score": 85
}}"""

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "")
                
                # Parse the JSON response from Ollama
                try:
                    parsed = json.loads(ai_response)
                    return {
                        "summary": parsed.get("summary", []),
                        "recommendations": parsed.get("recommendations", []),
                        "confidence_score": parsed.get("confidence_score", 75),
                        "ai_model": OLLAMA_MODEL
                    }
                except json.JSONDecodeError:
                    # If JSON parsing fails, extract text and use fallback
                    print(f"Failed to parse Ollama JSON response: {ai_response}")
                    return self._fallback_insights(footfall, avg_dwell, gender_dist, peak_hours, alert_count, period)
            else:
                print(f"Ollama API error: {response.status_code}")
                return self._fallback_insights(footfall, avg_dwell, gender_dist, peak_hours, alert_count, period)
                
        except requests.exceptions.ConnectionError:
            print("Ollama not running. Using fallback insights.")
            return self._fallback_insights(footfall, avg_dwell, gender_dist, peak_hours, alert_count, period)
        except requests.exceptions.Timeout:
            print("Ollama timeout. Using fallback insights.")
            return self._fallback_insights(footfall, avg_dwell, gender_dist, peak_hours, alert_count, period)
        except Exception as e:
            print(f"Ollama error: {e}")
            return self._fallback_insights(footfall, avg_dwell, gender_dist, peak_hours, alert_count, period)

    def _fallback_insights(self, footfall, avg_dwell, gender_dist, peak_hours, alert_count, period):
        """Fallback rule-based insights when Ollama is unavailable"""
        insights = []
        recommendations = []
        
        # Footfall insights
        if footfall > 0:
            if footfall > 100:
                insights.append(f"🎯 High traffic area with {footfall} unique visitors this {period}.")
                recommendations.append("Consider adding more staff during peak hours to improve customer service.")
            elif footfall > 50:
                insights.append(f"📊 Moderate traffic with {footfall} visitors this {period}.")
                recommendations.append("Monitor product placement to maximize engagement.")
            else:
                insights.append(f"📉 Low traffic area with only {footfall} visitors this {period}.")
                recommendations.append("Consider improving signage or product displays to attract more customers.")
        else:
            insights.append("⚠️ No visitor data recorded for this period.")
            recommendations.append("Ensure camera is properly positioned and processing is running.")
        
        # Dwell time insights
        if avg_dwell > 0:
            if avg_dwell > 60:
                insights.append(f"⏱️ Excellent engagement - visitors spend an average of {avg_dwell:.1f} seconds in this area.")
                recommendations.append("This area shows high interest. Consider adding promotional displays.")
            elif avg_dwell > 30:
                insights.append(f"⏱️ Good engagement with {avg_dwell:.1f} seconds average dwell time.")
            else:
                insights.append(f"⚡ Quick pass-through area with only {avg_dwell:.1f} seconds average time.")
                recommendations.append("Add eye-catching displays to encourage longer browsing.")
        
        # Gender insights
        total_gendered = sum(gender_dist.values()) if gender_dist else 0
        if total_gendered > 0:
            male_count = gender_dist.get('Male', 0)
            female_count = gender_dist.get('Female', 0)
            if male_count > female_count * 1.5:
                insights.append(f"👤 Predominantly male visitors ({male_count}/{total_gendered}).")
                recommendations.append("Consider stocking products that appeal to male demographics.")
            elif female_count > male_count * 1.5:
                insights.append(f"👤 Predominantly female visitors ({female_count}/{total_gendered}).")
                recommendations.append("Consider stocking products that appeal to female demographics.")
            else:
                insights.append(f"👥 Balanced gender distribution among visitors.")
        
        # Peak hours insights
        if peak_hours:
            hours_str = ", ".join([f"{h['hour']}:00" for h in peak_hours[:3]])
            insights.append(f"🕐 Peak visiting hours: {hours_str}")
            recommendations.append(f"Ensure adequate staffing during peak hours ({hours_str}).")
        
        # Alert insights
        if alert_count > 10:
            insights.append(f"🚨 High alert frequency ({alert_count} alerts) - possible security concern or bottleneck.")
            recommendations.append("Review camera footage during alert times to identify issues.")
        elif alert_count > 0:
            insights.append(f"ℹ️ {alert_count} dwell-time alerts recorded.")
        
        return {
            "summary": insights,
            "recommendations": recommendations,
            "confidence_score": min(95, 50 + (footfall * 0.3) + (avg_dwell * 0.2)),
            "ai_model": "fallback-rules"
        }

    def get_business_insights(self, cam_id=None):
        """Get overall business insights for shopkeeper dashboard"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Overall stats
                if cam_id:
                    cam_filter = "WHERE t.cam_id = %s"
                    params = (cam_id,)
                else:
                    cam_filter = ""
                    params = ()
                
                # Today's footfall
                cur.execute(f"""
                    SELECT COUNT(DISTINCT tracking_id) as today_footfall
                    FROM tracking t
                    {cam_filter}
                    {"AND" if cam_filter else "WHERE"} DATE(time) = CURRENT_DATE
                """, params)
                today = cur.fetchone()
                today_footfall = today['today_footfall'] if today else 0
                
                # Yesterday's footfall for comparison
                cur.execute(f"""
                    SELECT COUNT(DISTINCT tracking_id) as yesterday_footfall
                    FROM tracking t
                    {cam_filter}
                    {"AND" if cam_filter else "WHERE"} DATE(time) = CURRENT_DATE - INTERVAL '1 day'
                """, params)
                yesterday = cur.fetchone()
                yesterday_footfall = yesterday['yesterday_footfall'] if yesterday else 0
                
                # Week's footfall
                cur.execute(f"""
                    SELECT COUNT(DISTINCT tracking_id) as week_footfall
                    FROM tracking t
                    {cam_filter}
                    {"AND" if cam_filter else "WHERE"} time >= NOW() - INTERVAL '7 days'
                """, params)
                week = cur.fetchone()
                week_footfall = week['week_footfall'] if week else 0
                
                # Total alerts today
                cur.execute("""
                    SELECT COUNT(*) as alert_count
                    FROM alert
                    WHERE DATE(time) = CURRENT_DATE
                """)
                alerts = cur.fetchone()
                alert_count = alerts['alert_count'] if alerts else 0
                
                # Busiest region
                cur.execute("""
                    SELECT r.region_name, COUNT(DISTINCT t.tracking_id) as visitors
                    FROM tracking t
                    JOIN bounding_box b ON t.tracking_id = b.tracking_id AND t.video_shard = b.video_shard
                    JOIN region_defined r ON 
                        (b.x1 + b.x2) / 2 BETWEEN r.x1 AND r.x2
                        AND (b.y1 + b.y2) / 2 BETWEEN r.y1 AND r.y2
                    WHERE t.time >= NOW() - INTERVAL '1 day'
                    GROUP BY r.region_name
                    ORDER BY visitors DESC
                    LIMIT 1
                """)
                busiest = cur.fetchone()
                
                # Calculate change percentage
                change_pct = 0
                if yesterday_footfall > 0:
                    change_pct = round(((today_footfall - yesterday_footfall) / yesterday_footfall) * 100, 1)
                
                return {
                    "today": {
                        "footfall": today_footfall,
                        "change_from_yesterday": change_pct,
                        "trend": "up" if change_pct > 0 else "down" if change_pct < 0 else "stable"
                    },
                    "week": {
                        "total_footfall": week_footfall,
                        "daily_average": round(week_footfall / 7, 1)
                    },
                    "alerts_today": alert_count,
                    "busiest_region": {
                        "name": busiest['region_name'] if busiest else "N/A",
                        "visitors": busiest['visitors'] if busiest else 0
                    },
                    "quick_insights": self._generate_quick_insights(today_footfall, change_pct, alert_count)
                }
        except Exception as e:
            print(f"Error getting business insights: {e}")
            return {}

    def _generate_quick_insights(self, today_footfall, change_pct, alert_count):
        """Generate quick business insights using Ollama"""
        
        prompt = f"""You are a retail analytics AI. Generate 2-3 quick, actionable insights for a shopkeeper based on today's data:

- Today's Footfall: {today_footfall} visitors
- Change from Yesterday: {change_pct:+.1f}%
- Dwell-Time Alerts Today: {alert_count}

Provide short, emoji-prefixed insights (max 15 words each). Return as JSON array:
["insight1", "insight2", "insight3"]"""

        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "[]")
                try:
                    return json.loads(ai_response)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Quick insights Ollama error: {e}")
        
        # Fallback to rule-based
        insights = []
        if change_pct > 20:
            insights.append("📈 Traffic is significantly up today! Great day for sales.")
        elif change_pct > 0:
            insights.append("📊 Slight increase in visitors compared to yesterday.")
        elif change_pct < -20:
            insights.append("📉 Traffic is down significantly. Consider promotional activities.")
        elif change_pct < 0:
            insights.append("📊 Slightly fewer visitors than yesterday.")
        
        if today_footfall > 100:
            insights.append("🎯 High traffic day - ensure adequate staffing.")
        elif today_footfall < 10:
            insights.append("💡 Low traffic - good time for inventory management.")
        
        if alert_count > 5:
            insights.append("⚠️ Multiple dwell-time alerts - check for potential issues.")
        
        return insights

    def get_ai_recommendations(self, region_id):
        """Get AI-powered recommendations for a region"""
        try:
            report = self.generate_ai_report(region_id, "weekly")
            if "error" in report:
                return {"recommendations": [], "error": report["error"]}
            
            return {
                "region_name": report.get("region_name", "Unknown"),
                "recommendations": report.get("ai_insights", {}).get("recommendations", []),
                "metrics_summary": {
                    "footfall": report.get("metrics", {}).get("total_footfall", 0),
                    "avg_dwell": report.get("metrics", {}).get("avg_dwell_time_seconds", 0),
                    "alerts": report.get("metrics", {}).get("alert_count", 0)
                }
            }
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return {"recommendations": [], "error": str(e)}

    def generate_daily_insights(self):
        """Generate and store daily insights for all regions"""
        try:
            regions = self.get_all_regions()
            count = 0
            
            for region in regions:
                region_id = region['region_id']
                report = self.generate_ai_report(region_id, "daily")
                
                if "error" not in report:
                    insight_id = int(str(uuid.uuid4().int)[:8])
                    self.add_region_insight(
                        insight_id=insight_id,
                        date=datetime.now().date(),
                        tracking_group_info=str(report.get("ai_insights", {})),
                        total_footfall=report.get("metrics", {}).get("total_footfall", 0),
                        region_id=region_id
                    )
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error generating daily insights: {e}")
            return 0

if __name__ == "__main__":
    orm = DataBaseOrm()
    # Test CRUD
    # 1. Create
    orm.add_camera(1, "Test Camera")
    
    # 2. Read
    cam = orm.get_camera(1)
    print(f"Retrieved Camera: {cam}")
    
    # 3. Update
    orm.update_camera(1, "Updated Camera Name", "DISABLED")
    cam = orm.get_camera(1)
    print(f"Updated Camera: {cam}")
    
    # 4. Delete
    # orm.delete_camera(1)
    # print("Camera deleted")

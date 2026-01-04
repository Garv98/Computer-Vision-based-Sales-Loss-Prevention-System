import psycopg2 
from psycopg2.extras import DictCursor, execute_values
conn = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="diptanshu",
    dbname="salesloss"
)

class DataBaseOrm:
    def __init__(self):
        self.conn = psycopg2.connect(
                    host="localhost",
                    user="postgres",
                    password="diptanshu",
                    dbname="salesloss"
                )
        self.cursor = self.conn.cursor(cursor_factory= DictCursor)

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
        """
        try:
            # First get region coordinates
            region = self.get_region(region_id)
            if not region:
                return []
            
            rx1, rx2, ry1, ry2 = region['x1'], region['x2'], region['y1'], region['y2']
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                # Query to count unique tracking_ids whose bounding box center falls within region
                # Center x = (x1+x2)/2, Center y = (y1+y2)/2
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
    def add_region_insight(self, insight_id, date, tracking_group_info, total_footfall):
        try:
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
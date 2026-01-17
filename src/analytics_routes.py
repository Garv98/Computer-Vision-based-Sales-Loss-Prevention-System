from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io
import json
from database import DataBaseOrm

router = APIRouter()
orm = DataBaseOrm()

@router.get("/export/analytics/csv/{region_id}")
async def export_analytics_csv(region_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Export analytics data as CSV"""
    try:
        # Get all analytics data
        footfall = orm.get_footfall_by_region(region_id)
        time_spent = orm.get_time_spent_in_region(region_id)
        demographics = orm.get_demographics_stats(region_id)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Report Type', 'Analytics Export'])
        writer.writerow(['Region ID', region_id])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Footfall data
        writer.writerow(['Footfall by Shard'])
        writer.writerow(['Shard ID', 'Count'])
        for shard_id, count in footfall:
            writer.writerow([shard_id, count])
        writer.writerow([])
        
        # Time spent data
        writer.writerow(['Average Time Spent by Shard'])
        writer.writerow(['Shard ID', 'Avg Time (seconds)'])
        for shard_id, avg_time in time_spent:
            writer.writerow([shard_id, f'{avg_time:.2f}'])
        writer.writerow([])
        
        # Demographics
        writer.writerow(['Demographics'])
        writer.writerow(['Gender', 'Count'])
        for demo in demographics:
            writer.writerow([demo['gender'], demo['count']])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=analytics_region_{region_id}_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/analytics/trends/daily")
async def get_daily_trends(region_id: Optional[int] = None, days: int = 7):
    """Get daily footfall trends for the past N days"""
    try:
        trends = orm.get_daily_trends(region_id, days)
        return {"period": "daily", "days": days, "data": trends}
    except Exception as e:
        raise HTTPException(500, f"Failed to get trends: {str(e)}")


@router.get("/analytics/trends/weekly")
async def get_weekly_trends(region_id: Optional[int] = None, weeks: int = 4):
    """Get weekly footfall trends for the past N weeks"""
    try:
        trends = orm.get_weekly_trends(region_id, weeks)
        return {"period": "weekly", "weeks": weeks, "data": trends}
    except Exception as e:
        raise HTTPException(500, f"Failed to get trends: {str(e)}")


@router.get("/analytics/trends/monthly")
async def get_monthly_trends(region_id: Optional[int] = None, months: int = 6):
    """Get monthly footfall trends for the past N months"""
    try:
        trends = orm.get_monthly_trends(region_id, months)
        return {"period": "monthly", "months": months, "data": trends}
    except Exception as e:
        raise HTTPException(500, f"Failed to get trends: {str(e)}")


@router.get("/analytics/heatmap/{region_id}")
async def get_heatmap_data(region_id: int, shard_id: Optional[str] = None, resolution: int = 50):
    """Generate heat map data for a region based on bounding box density"""
    try:
        heatmap = orm.get_heatmap_data(region_id, shard_id, resolution)
        return {"region_id": region_id, "resolution": resolution, "data": heatmap}
    except Exception as e:
        raise HTTPException(500, f"Failed to generate heatmap: {str(e)}")

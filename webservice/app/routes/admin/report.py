from flask import Blueprint, jsonify, request
from app import db
from app.models import *
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.sql import or_, and_

report = Blueprint('report', __name__)

@report.route('/api/report/market_share', methods=['GET'])
def get_market_share():
    """Gets market share by airlines with time filters."""
    try:
        # Lấy tham số thời gian từ query string
        time_filter = request.args.get('time', 'today')  # Mặc định là 'today'
        now = datetime.now()

        # Tính khoảng thời gian filter
        if time_filter == 'today':
            start_date = now.date()
            end_date = start_date + timedelta(days=1)
        elif time_filter == 'yesterday':
            start_date = (now - timedelta(days=1)).date()
            end_date = start_date + timedelta(days=1)
        elif time_filter == 'last_7_days':
            start_date = (now - timedelta(days=7)).date()
            end_date = now.date() + timedelta(days=1)
        elif time_filter == 'last_14_days':
            start_date = (now - timedelta(days=14)).date()
            end_date = now.date() + timedelta(days=1)
        elif time_filter == 'last_21_days':
            start_date = (now - timedelta(days=21)).date()
            end_date = now.date() + timedelta(days=1)
        elif time_filter == 'last_month':
            start_date = (now - timedelta(days=30)).date()
            end_date = now.date() + timedelta(days=1)
        else:
            return jsonify({"status": "error", "message": "Invalid time filter"}), 400

        # Tính tổng số đặt chỗ và thị phần
        total_bookings = db.session.query(
            HangHangKhong.MaHHK,
            HangHangKhong.TenHHK,
            func.count(DatCho.MaDatCho).label('booking_count')
        ).join(
            MayBay, HangHangKhong.MaHHK == MayBay.MaHHK
        ).join(
            ChuyenBay, MayBay.MaMayBay == ChuyenBay.MaMB
        ).join(
            DatCho, ChuyenBay.MaChuyenBay == DatCho.MaCB
        ).filter(
            DatCho.TrangThai == 'Đã thanh toán',
            func.date(DatCho.NgayMua) >= start_date,
            func.date(DatCho.NgayMua) < end_date
        ).group_by(
            HangHangKhong.MaHHK,
            HangHangKhong.TenHHK
        ).all()

        # Tính tổng số lượng đặt chỗ
        total = sum(booking.booking_count for booking in total_bookings)

        # Tạo kết quả trả về
        result = [
            {
                "airline_code": booking.MaHHK,
                "airline_name": booking.TenHHK,
                "total_bookings": int(booking.booking_count),
                "market_share": round((booking.booking_count / total * 100), 1) if total > 0 else 0.0
            }
            for booking in total_bookings
        ]

        return jsonify({"status": "success", "data": result, "time_filter": time_filter}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@report.route('/api/report/revenue', methods=['GET'])
def get_revenue_report():
    try:
        current_date = datetime.now()

        # Lấy các tham số từ query string
        report_type = request.args.get('type', 'monthly')
        month = request.args.get('month', str(current_date.month))  # 'all' hoặc chuỗi số
        year = request.args.get('year', str(current_date.year))     # 'all' hoặc chuỗi số
        include_growth = request.args.get('include_growth', 'false').lower() == 'true'

        if report_type == 'monthly':
            # === TÍNH DOANH THU THEO NGÀY ===
            base_query = db.session.query(
                func.date(DatCho.NgayMua).label('date'),
                func.count(DatCho.MaDatCho).label('total_orders'),
                func.coalesce(func.sum(ThanhToan.SoTien), 0).label('total_revenue')
            ).join(
                ThanhToan, DatCho.MaDatCho == ThanhToan.MaDatCho
            ).filter(
                DatCho.TrangThai == 'Đã thanh toán'
            )

            # Nếu month != 'all', lọc thêm theo tháng
            if month != 'all':
                base_query = base_query.filter(func.month(DatCho.NgayMua) == int(month))

            # Nếu year != 'all', lọc thêm theo năm
            if year != 'all':
                base_query = base_query.filter(func.year(DatCho.NgayMua) == int(year))

            query = base_query.group_by(
                func.date(DatCho.NgayMua)
            ).order_by(
                func.date(DatCho.NgayMua)
            )

            # Trả kết quả
            result = [
                {
                    "date": record.date.strftime('%Y-%m-%d'),
                    "total_orders": int(record.total_orders),
                    "total_revenue": float(record.total_revenue)
                }
                for record in query.all()
            ]

        elif report_type == 'weekly':
            base_query = db.session.query(
                func.week(DatCho.NgayMua).label('week_number'),
                func.year(DatCho.NgayMua).label('year'),
                func.count(DatCho.MaDatCho).label('total_orders'),
                func.coalesce(func.sum(ThanhToan.SoTien), 0).label('total_revenue')
            ).join(
                ThanhToan, DatCho.MaDatCho == ThanhToan.MaDatCho
            ).filter(
                DatCho.TrangThai == 'Đã thanh toán'
            )

            # Lọc theo tháng và năm (nếu có)
            if month != 'all':
                base_query = base_query.filter(func.month(DatCho.NgayMua) == int(month))
            if year != 'all':
                base_query = base_query.filter(func.year(DatCho.NgayMua) == int(year))

            query = base_query.group_by(
                func.week(DatCho.NgayMua),
                func.year(DatCho.NgayMua)
            ).order_by(
                func.year(DatCho.NgayMua),
                func.week(DatCho.NgayMua)
            )

            weekly_data = query.all()
            # Chuyển kết quả raw thành danh sách dict
            result = [
                {
                    "week_number": int(week.week_number),
                    "year": int(week.year),
                    "total_orders": int(week.total_orders),
                    "total_revenue": float(week.total_revenue)
                }
                for week in weekly_data
            ]

            # Nếu có yêu cầu tính tăng trưởng
            if include_growth:
                # Lấy tất cả các tuần từ database (bao gồm cả năm trước nếu cần)
                full_query = db.session.query(
                    func.week(DatCho.NgayMua).label('week_number'),
                    func.year(DatCho.NgayMua).label('year'),
                    func.count(DatCho.MaDatCho).label('total_orders'),
                    func.coalesce(func.sum(ThanhToan.SoTien), 0).label('total_revenue')
                ).join(
                    ThanhToan, DatCho.MaDatCho == ThanhToan.MaDatCho
                ).filter(
                    DatCho.TrangThai == 'Đã thanh toán'
                ).group_by(
                    func.week(DatCho.NgayMua),
                    func.year(DatCho.NgayMua)
                ).order_by(
                    func.year(DatCho.NgayMua),
                    func.week(DatCho.NgayMua)
                )

                full_data = full_query.all()
                full_result = [
                    {
                        "week_number": int(week.week_number),
                        "year": int(week.year),
                        "total_orders": int(week.total_orders),
                        "total_revenue": float(week.total_revenue)
                    }
                    for week in full_data
                ]

                # Tạo dictionary để tra cứu tuần trước
                full_result_sorted = sorted(full_result, key=lambda x: (x['year'], x['week_number']))
                prev_week_map = {}
                for i, row in enumerate(full_result_sorted):
                    if i > 0:  # Bắt đầu từ tuần thứ hai
                        prev_week_map[(row['year'], row['week_number'])] = full_result_sorted[i - 1]

                # Tính tăng trưởng
                for row in result:
                    key = (row['year'], row['week_number'])
                    if key in prev_week_map:
                        prev_revenue = prev_week_map[key]["total_revenue"]
                        current_revenue = row["total_revenue"]
                        if prev_revenue != 0:
                            row["growth_rate"] = round((current_revenue - prev_revenue) / prev_revenue * 100, 2)
                        else:
                            row["growth_rate"] = 0
                    else:
                        row["growth_rate"] = 0

        else:
            # Nếu type không hợp lệ, trả về lỗi
            return jsonify({
                "status": "error",
                "message": "Invalid report type. Use 'monthly' or 'weekly'."
            }), 400

        return jsonify({
            "status": "success",
            "data": result,
            "report_type": report_type,
            "month": month,
            "year": year
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@report.route('/api/report/passengers', methods=['GET']) 
def get_passengers():
    try:
        # Count total users and passengers
        total_users = NguoiDung.query.filter_by(MaNND=2).count()
        total_passengers = HanhKhach.query.count()
        
        # Calculate percentage of users compared to passengers
        user_passenger_ratio = 0
        if total_passengers > 0:
            user_passenger_ratio = round((total_passengers / total_users) * 100, 2)
        
        # Prepare response
        result = {
            "total_users": total_users,
            "total_passengers": total_passengers,
            "user_passenger_ratio": user_passenger_ratio
        }
        
        return jsonify({"status": "success", "data": result}), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@report.route('/api/report/booking_stats', methods=['GET'])
def get_booking_stats():
    """Gets booking statistics for different time periods."""
    try:
        # Get time range from request
        time_range = request.args.get('time_range', 'last_7_days')
        
        # Get current date at start of day
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Define date range based on time_range
        if time_range == 'today':
            start_date = today
            end_date = datetime.now()
        elif time_range == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today
        elif time_range == 'last_7_days':
            start_date = today - timedelta(days=7)
            end_date = datetime.now()
        elif time_range == 'last_14_days':
            start_date = today - timedelta(days=14)
            end_date = datetime.now()
        elif time_range == 'last_21_days':
            start_date = today - timedelta(days=21)
            end_date = datetime.now()
        elif time_range == 'last_month':
            start_date = today - timedelta(days=30)
            end_date = today
        else:  # last_3_months
            start_date = today - timedelta(days=90)
            end_date = datetime.now()

        # Query daily booking stats for the specified period
        stats = db.session.query(
            func.date(DatCho.NgayMua).label('date'),
            func.count(DatCho.MaDatCho).label('total_bookings'),
            func.sum(DatCho.SoLuongGheBus + DatCho.SoLuongGheEco).label('total_passengers')
        ).filter(
            DatCho.NgayMua.between(start_date, end_date)
        ).group_by(
            func.date(DatCho.NgayMua)
        ).order_by(
            func.date(DatCho.NgayMua)
        ).all()

        # Format results
        result = [{
            'date': stat.date.strftime('%Y-%m-%d'),
            'total_bookings': int(stat.total_bookings or 0),
            'total_passengers': int(stat.total_passengers or 0)
        } for stat in stats]

        # Calculate cumulative totals
        total_bookings = sum(item['total_bookings'] for item in result)
        total_passengers = sum(item['total_passengers'] for item in result)

        return jsonify({
            "status": "success",
            "data": {
                "stats": result,
                "total_bookings": total_bookings,
                "total_passengers": total_passengers
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@report.route('/api/report/baggage_service_stats', methods=['GET'])
def get_baggage_service_stats():
    """Gets baggage service statistics for different time periods."""
    try:
        
        # Get time range from request
        time_range = request.args.get('time_range', 'last_7_days')
        
        # Get current date at start of day
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Define date range based on time_range
        if time_range == 'today':
            start_date = today
            end_date = datetime.now()
        elif time_range == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today
        elif time_range == 'last_7_days':
            start_date = today - timedelta(days=7)
            end_date = datetime.now()
        elif time_range == 'last_14_days':
            start_date = today - timedelta(days=14)
            end_date = datetime.now()
        elif time_range == 'last_21_days':
            start_date = today - timedelta(days=21)
            end_date = datetime.now()
        elif time_range == 'last_month':
            start_date = today - timedelta(days=31)
            end_date = datetime.now()
        else:  # last_3_months
            start_date = today - timedelta(days=93)
            end_date = datetime.now()
        print(start_date, "-", end_date)

        # Query statistics
        stats = db.session.query(
            DichVuHanhLy.SoKy.label('weight'),
            func.count(ChiTietDatCho.MaDatCho).label('bookings'),
            func.sum(DichVuHanhLy.Gia).label('revenue')
        ).join(
            ChiTietDatCho, DichVuHanhLy.MaDichVu == ChiTietDatCho.MaDichVu
        ).join(
            DatCho, ChiTietDatCho.MaDatCho == DatCho.MaDatCho
        ).filter(
            DatCho.NgayMua.between(start_date, end_date)
        ).group_by(
            DichVuHanhLy.SoKy
        ).order_by(
            DichVuHanhLy.SoKy
        ).all()

        # Format results
        result = [{
            'weight': f'{stat.weight}kg',
            'bookings': int(stat.bookings),
            'revenue': float(stat.revenue),
            'percentage': 0  # Will be calculated below
        } for stat in stats]

        # Calculate percentages
        total_bookings = sum(item['bookings'] for item in result)
        if total_bookings > 0:
            for item in result:
                item['percentage'] = round(item['bookings'] / total_bookings * 100, 1)

        return jsonify({
            "status": "success",
            "data": {
                "stats": result,
                "total_bookings": total_bookings,
                "total_revenue": sum(item['revenue'] for item in result)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
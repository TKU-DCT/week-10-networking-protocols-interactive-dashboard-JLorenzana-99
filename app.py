import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="System Monitor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "log.db"

# Initialize session state for settings
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'refresh_interval' not in st.session_state:
    st.session_state.refresh_interval = 30

# Apply custom theme styling
if st.session_state.dark_mode:
    st.markdown("""
        <style>
        /* Main app background */
        .stApp {
            background-color: #0E1117;
            color: #FFFFFF;
        }
        
        /* Remove white header bar */
        header {
            background-color: #0E1117 !important;
        }
        
        /* Top toolbar */
        .stAppToolbar {
            background-color: #0E1117 !important;
        }
        
        /* Sidebar */
        .stSidebar {
            background-color: #262730;
        }
        
        /* Text colors */
        .stMarkdown, .stText, p, span, label {
            color: #FFFFFF !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #FFFFFF !important;
        }
        
        /* Metrics */
        .stMetric label {
            color: #FFFFFF !important;
        }
        .stMetric .metric-value {
            color: #FFFFFF !important;
        }
                
        /* All emotion cache text elements */
        [class*="st-emotion-cache"] {
            color: #FFFFFF !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #262730;
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        /* Main app background */
        .stApp {
            background-color: #FFFFFF;
            color: #262730;
        }
        
        /* Header */
        header {
            background-color: #FFFFFF !important;
        }
        
        /* Top toolbar */
        .stAppToolbar {
            background-color: #FFFFFF !important;
        }
        
        /* Sidebar */
        .stSidebar {
            background-color: #F0F2F6;
        }
        
        /* Text colors */
        .stMarkdown, .stText, p, span, label {
            color: #262730 !important;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #262730 !important;
        }
        
        /* Metrics */
        .stMetric label {
            color: #262730 !important;
        }
        .stMetric .metric-value {
            color: #262730 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Database connection functions
@st.cache_data(ttl=10)
def get_system_logs(ping_filter=None, date_filter=None, cpu_threshold=None):
    """Fetch system logs from database with optional filters"""
    conn = sqlite3.connect(DB_NAME)
    
    conditions = []
    params = []
    
    if ping_filter and ping_filter != "All":
        conditions.append("ping_status = ?")
        params.append(ping_filter)
    
    if date_filter:
        start_date, end_date = date_filter
        conditions.append("DATE(timestamp) BETWEEN ? AND ?")
        params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
    
    if cpu_threshold is not None:
        conditions.append("cpu >= ?")
        params.append(cpu_threshold)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM system_log WHERE {where_clause} ORDER BY id DESC"
    
    df = pd.read_sql_query(query, conn, params=params if params else None)
    conn.close()
    return df

@st.cache_data(ttl=10)
def get_alerts_log():
    """Fetch alerts from database"""
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM alerts_log ORDER BY id DESC LIMIT 50"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=10)
def get_statistics():
    """Get database statistics"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM system_log")
    log_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts_log")
    alert_count = cursor.fetchone()[0]
    
    # Get latest metrics
    cursor.execute("""
        SELECT cpu, memory, disk, ping_status, ping_ms 
        FROM system_log 
        ORDER BY id DESC 
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    # Get threshold violations count
    cursor.execute("SELECT COUNT(*) FROM system_log WHERE cpu > 80 OR memory > 85 OR disk > 90")
    threshold_violations = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'log_count': log_count,
        'alert_count': alert_count,
        'threshold_violations': threshold_violations,
        'latest_cpu': latest[0] if latest else 0,
        'latest_memory': latest[1] if latest else 0,
        'latest_disk': latest[2] if latest else 0,
        'latest_ping_status': latest[3] if latest else "N/A",
        'latest_ping_ms': latest[4] if latest else 0
    }

def dashboard_page():
    """Main dashboard page"""
    st.title("📊 System Monitor Dashboard")
    st.markdown("---")
    
    # Filters in columns
    st.subheader("🔍 Filters")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        ping_filter = st.selectbox("Ping Status", ["All", "UP", "DOWN"])
    
    with filter_col2:
        cpu_threshold = st.slider("CPU Threshold (%)", 0, 100, 0, 5)
    
    with filter_col3:
        use_date_filter = st.checkbox("Enable Date Filter")
    
    with filter_col4:
        num_records = st.slider("Records to Display", 5, 100, 20)
    
    # Date filter
    date_filter = None
    if use_date_filter:
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        with date_col2:
            end_date = st.date_input("End Date", datetime.now())
        date_filter = (start_date, end_date)
    
    st.markdown("---")
    
    # Get data
    try:
        stats = get_statistics()
        
        # Display key metrics
        st.header("📈 Current System Status")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("CPU Usage", f"{stats['latest_cpu']:.1f}%", 
                     delta=f"{stats['latest_cpu'] - 80:.1f}%" if stats['latest_cpu'] > 80 else None,
                     delta_color="inverse")
        
        with col2:
            st.metric("Memory Usage", f"{stats['latest_memory']:.1f}%",
                     delta=f"{stats['latest_memory'] - 85:.1f}%" if stats['latest_memory'] > 85 else None,
                     delta_color="inverse")
        
        with col3:
            st.metric("Disk Usage", f"{stats['latest_disk']:.1f}%",
                     delta=f"{stats['latest_disk'] - 90:.1f}%" if stats['latest_disk'] > 90 else None,
                     delta_color="inverse")
        
        with col4:
            ping_status_icon = "🟢" if stats['latest_ping_status'] == "UP" else "🔴"
            st.metric("Ping Status", f"{ping_status_icon} {stats['latest_ping_status']}")
        
        with col5:
            ping_display = f"{stats['latest_ping_ms']:.1f}ms" if stats['latest_ping_ms'] > 0 else "N/A"
            st.metric("Ping Time", ping_display)
        
        with col6:
            st.metric("Alert Count", stats['threshold_violations'], 
                     delta=f"{stats['threshold_violations']}" if stats['threshold_violations'] > 0 else "0",
                     delta_color="inverse")
        
        st.markdown("---")
        
        # Alerts section
        st.header("🚨 Recent Alerts")
        alerts_df = get_alerts_log()
        
        if not alerts_df.empty:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Total Alerts", stats['alert_count'])
            
            with st.expander(f"View Latest {min(20, len(alerts_df))} Alerts", expanded=False):
                for _, alert in alerts_df.head(20).iterrows():
                    alert_color = {
                        'CPU': '🔴',
                        'MEMORY': '🟠',
                        'DISK': '🟡',
                        'PING': '🔵'
                    }.get(alert['alert_type'], '⚪')
                    
                    st.warning(f"{alert_color} **{alert['timestamp']}** - {alert['message']}")
        else:
            st.success("✅ No alerts triggered! All systems operating normally.")
        
        st.markdown("---")
        
        # System logs table
        st.header("📋 System Logs")
        df = get_system_logs(
            ping_filter if ping_filter != "All" else None,
            date_filter,
            cpu_threshold if cpu_threshold > 0 else None
        )
        
        if not df.empty:
            st.info(f"Showing {min(num_records, len(df))} of {len(df)} filtered records (Total: {stats['log_count']})")
            
            display_df = df.head(num_records).copy()
            display_df['cpu'] = display_df['cpu'].apply(lambda x: f"{x:.1f}%")
            display_df['memory'] = display_df['memory'].apply(lambda x: f"{x:.1f}%")
            display_df['disk'] = display_df['disk'].apply(lambda x: f"{x:.1f}%")
            display_df['ping_ms'] = display_df['ping_ms'].apply(lambda x: f"{x:.1f}ms" if x > 0 else "N/A")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No data available matching the current filters.")
            return
        
        st.markdown("---")
        
        # Charts section
        st.header("📊 Performance Charts")
        
        # Use filtered data for charts
        chart_df = df.sort_values('id')
        
        if not chart_df.empty:
            chart_data = chart_df[['timestamp', 'cpu', 'memory', 'disk']].copy()
            chart_data = chart_data.rename(columns={
                'cpu': 'CPU %',
                'memory': 'Memory %',
                'disk': 'Disk %'
            })
            chart_data['timestamp'] = pd.to_datetime(chart_data['timestamp'])
            chart_data = chart_data.set_index('timestamp')
            
            st.subheader("System Resource Usage Over Time")
            st.line_chart(chart_data, height=400)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption("🔴 CPU Threshold: 80%")
            with col2:
                st.caption("🟠 Memory Threshold: 85%")
            with col3:
                st.caption("🟡 Disk Threshold: 90%")
            
            st.markdown("---")
            
            # Ping Response Time Chart
            st.subheader("Network Ping Response Time")
            
            ping_df = chart_df[chart_df['ping_ms'] > 0].copy()
            
            if not ping_df.empty:
                ping_chart = ping_df[['timestamp', 'ping_ms']].copy()
                ping_chart['timestamp'] = pd.to_datetime(ping_chart['timestamp'])
                ping_chart = ping_chart.set_index('timestamp')
                ping_chart = ping_chart.rename(columns={'ping_ms': 'Ping (ms)'})
                
                st.line_chart(ping_chart, height=300, color='#6C5CE7')
            else:
                st.info("No successful ping data available for current filters.")
            
            st.markdown("---")
            
            # Summary statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Average Resource Usage")
                avg_stats = pd.DataFrame({
                    'Metric': ['CPU', 'Memory', 'Disk'],
                    'Average (%)': [
                        f"{chart_df['cpu'].mean():.2f}",
                        f"{chart_df['memory'].mean():.2f}",
                        f"{chart_df['disk'].mean():.2f}"
                    ],
                    'Max (%)': [
                        f"{chart_df['cpu'].max():.2f}",
                        f"{chart_df['memory'].max():.2f}",
                        f"{chart_df['disk'].max():.2f}"
                    ],
                    'Min (%)': [
                        f"{chart_df['cpu'].min():.2f}",
                        f"{chart_df['memory'].min():.2f}",
                        f"{chart_df['disk'].min():.2f}"
                    ]
                })
                st.dataframe(avg_stats, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("🌐 Ping Status Summary")
                ping_counts = chart_df['ping_status'].value_counts()
                ping_summary = pd.DataFrame({
                    'Status': ping_counts.index,
                    'Count': ping_counts.values,
                    'Percentage': [f"{(count/len(chart_df)*100):.1f}%" for count in ping_counts.values]
                })
                st.dataframe(ping_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for charts with current filters.")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure 'log.db' exists in the same directory. Run your logger script first.")

def settings_page():
    """Settings page"""
    st.title("⚙️ Settings")
    st.markdown("---")
    
    st.subheader("🎨 Appearance Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("🔄 Auto-Refresh Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        auto_refresh = st.toggle("Enable Auto-Refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto_refresh
    
    with col2:
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (seconds)", 10, 300, st.session_state.refresh_interval, 10)
            st.session_state.refresh_interval = refresh_interval
            st.info(f"Dashboard will refresh every {refresh_interval} seconds")
    
    st.markdown("---")
    
    st.subheader("🗄️ Database Settings")
    st.text_input("Database Name", value=DB_NAME, disabled=True)
    st.caption("The database file used for storing system logs and alerts")
    
    st.markdown("---")
    
    st.subheader("📊 Threshold Settings")
    st.markdown("""
    **Current Alert Thresholds:**
    - 🔴 CPU: 80%
    - 🟠 Memory: 85%
    - 🟡 Disk: 90%
    
    These thresholds determine when alerts are triggered in the monitoring system.
    """)
    
    st.markdown("---")
    
    st.subheader("💾 Data Management")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared successfully!")
    
    with col2:
        st.caption("Clear cached data to force reload from database")

def about_page():
    """About page"""
    st.title("ℹ️ About")
    st.markdown("---")
    
    st.markdown("""
    ## 📊 System Monitor Dashboard
    
    **Version:** 2.0.0  
    **Last Updated:** November 2024
    
    ### 🎯 Purpose
    
    This dashboard provides real-time monitoring and visualization of system performance metrics including:
    - CPU Usage
    - Memory Usage
    - Disk Usage
    - Network Ping Status
    - System Alerts
    
    ### ✨ Features
    
    - **Real-time Monitoring**: Track system metrics as they're collected
    - **Alert Management**: View and track system alerts when thresholds are exceeded
    - **Interactive Filtering**: Filter data by ping status, CPU threshold, and date range
    - **Visual Analytics**: Charts and graphs for trend analysis
    - **Dark Mode**: Toggle between light and dark themes
    - **Auto-Refresh**: Automatic data updates at configurable intervals
    
    ### 🛠️ Technology Stack
    
    - **Streamlit**: Web application framework
    - **SQLite**: Database for storing logs
    - **Pandas**: Data manipulation and analysis
    - **Python**: Core programming language
    
    ### 📊 Data Collection
    
    The dashboard reads from a SQLite database (`log.db`) containing two main tables:
    
    1. **system_log**: System metrics (CPU, Memory, Disk, Ping)
    2. **alerts_log**: Alert records when thresholds are exceeded
    
    ### 🚀 Usage
    
    1. **Dashboard**: View real-time metrics and historical data
    2. **Settings**: Configure appearance and refresh settings
    3. **About**: Learn more about the application
    
    ### 📝 Notes
    
    - Data is cached for 10 seconds to optimize performance
    - Use the refresh button in the sidebar to manually update data
    - Enable auto-refresh in Settings for continuous monitoring
    """)

# Sidebar navigation
def sidebar_navigation():
    """Create sidebar navigation menu"""
    with st.sidebar:
        # Logo/Header
        st.markdown("""
            <div style='text-align: center; padding: 20px 0;'>
                <h1 style='margin: 0; font-size: 24px;'>📊 SysMonitor</h1>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        # Navigation menu
        st.header("📋 Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "Settings", "About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Quick actions
        st.header("⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Auto-refresh status
        if st.session_state.auto_refresh:
            st.success(f"✅ Auto-refresh: {st.session_state.refresh_interval}s")
        else:
            st.info("⏸️ Auto-refresh: Disabled")
        
        st.markdown("---")
        
        # Database info
        st.header("💾 Database")
        try:
            stats = get_statistics()
            st.metric("Total Records", stats['log_count'])
            st.metric("Total Alerts", stats['alert_count'])
            st.metric("Violations", stats['threshold_violations'])
        except:
            st.warning("Database not connected")
        
        st.markdown("---")
        st.caption("System Monitor v2.0")
        
    return page

# Main application
def main():
    # Sidebar navigation
    page = sidebar_navigation()
    
    # Route to appropriate page
    if page == "Dashboard":
        dashboard_page()
    elif page == "Settings":
        settings_page()
    elif page == "About":
        about_page()
    
    # Handle auto-refresh at the end (only on Dashboard)
    if st.session_state.auto_refresh and page == "Dashboard":
        import time
        time.sleep(st.session_state.refresh_interval)
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
"""
Ervin's AI Social Media Dashboard - Main UI
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import logging

from database.connection import SessionLocal


from app.database.crud import (
    crud_comment, crud_reply, crud_post, crud_settings, 
    crud_analytics, crud_content, crud_ghl
)
from app.core.ai_processor import AIProcessor
from app.core.comment_processor import CommentProcessor
from app.core.content_generator import ContentGenerator
from app.utils.scheduler import TaskScheduler
from app.utils.helpers import (
    time_ago, format_number, get_platform_icon, 
    validate_api_keys, truncate_text
)
from app.config import COMMENT_TYPES, settings

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Ervin's AI Social Media Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Dark theme enhancements */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Comment cards */
    .comment-card {
        background-color: #1e2329;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .comment-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(31, 119, 180, 0.3);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-pending { background-color: #ff9800; color: white; }
    .status-approved { background-color: #4caf50; color: white; }
    .status-rejected { background-color: #f44336; color: white; }
    .status-posted { background-color: #2196f3; color: white; }
    
    /* Platform badges */
    .platform-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .youtube { background-color: #ff0000; color: white; }
    .facebook { background-color: #1877f2; color: white; }
    .instagram { background-color: #e4405f; color: white; }
    .linkedin { background-color: #0077b5; color: white; }
    .twitter { background-color: #1da1f2; color: white; }
    
    /* Metric cards */
    .metric-card {
        background-color: #1e2329;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #2d3339;
    }
    
    /* AI reply card */
    .ai-reply-card {
        background-color: #162d3d;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #1f77b4;
        margin-top: 0.5rem;
    }
    
    /* Success animation */
    @keyframes successPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .success-animation {
        animation: successPulse 0.5s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scheduler' not in st.session_state:
    st.session_state.scheduler = TaskScheduler()
    st.session_state.scheduler.start()

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = True

if 'show_test_comment' not in st.session_state:
    st.session_state.show_test_comment = False

# Initialize processors
@st.cache_resource
def get_processors():
    return {
        'ai': AIProcessor(),
        'comment': CommentProcessor(),
        'content': ContentGenerator()
    }

processors = get_processors()

# Database session
def get_db():
    return SessionLocal()

# Header
st.title("🤖 Ervin's AI Social Media Command Center")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    # API Status
    api_status = validate_api_keys()
    st.subheader("🔌 API Connections")
    
    cols = st.columns(2)
    for i, (api, status) in enumerate(api_status.items()):
        with cols[i % 2]:
            if status:
                st.success(f"✅ {api.upper()}")
            else:
                st.error(f"❌ {api.upper()}")
    
    st.markdown("---")
    
    # Owner Activity Control
    db = get_db()
    owner_active = crud_settings.get_owner_active(db)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Mode", 
            "Manual" if owner_active else "AI Auto",
            delta="Owner Active" if owner_active else "AI Active"
        )
    
    with col2:
        new_owner_active = st.toggle("Owner Control", value=owner_active)
        if new_owner_active != owner_active:
            crud_settings.set_owner_active(db, new_owner_active)
            st.success("Mode updated!")
            st.rerun()
    
    db.close()
    
    st.markdown("---")
    
    # Filters
    st.subheader("🔍 Filters")
    
    platforms = st.multiselect(
        "Platforms",
        ["youtube", "facebook", "instagram", "linkedin", "twitter"],
        default=["youtube", "facebook", "instagram"]
    )
    
    comment_types = st.multiselect(
        "Comment Types",
        list(COMMENT_TYPES.keys()),
        default=["lead", "praise", "question"]
    )
    
    time_range = st.selectbox(
        "Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
        index=1
    )
    
    # Auto-refresh
    st.session_state.auto_refresh = st.checkbox(
        "Auto-refresh (10s)", 
        value=st.session_state.auto_refresh
    )
    
    # Manual Test Comment (Removable Feature)
    st.markdown("---")
    if st.checkbox("🧪 Test Mode"):
        st.session_state.show_test_comment = True
    else:
        st.session_state.show_test_comment = False

# Calculate time range
def get_time_range(range_str: str):
    now = datetime.utcnow()
    if range_str == "Last Hour":
        return now - timedelta(hours=1), now
    elif range_str == "Last 24 Hours":
        return now - timedelta(days=1), now
    elif range_str == "Last 7 Days":
        return now - timedelta(days=7), now
    elif range_str == "Last 30 Days":
        return now - timedelta(days=30), now
    else:
        return None, now

# Main content area
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Live Feed", 
    "🤖 AI Replies", 
    "📝 Content Generator",
    "📊 Analytics",
    "⚡ GHL Actions"
])

# Tab 1: Live Comment Feed
with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader("💬 Real-Time Comment Stream")
    with col2:
        if st.button("🔄 Refresh", key="refresh_comments"):
            st.rerun()
    with col3:
        bulk_action = st.selectbox(
            "Bulk Actions",
            ["Select...", "Approve All AI", "Generate Replies"],
            key="bulk_action"
        )
    
    # Manual Test Comment Feature (Removable)
    if st.session_state.show_test_comment:
        with st.expander("🧪 Test AI Reply Generation", expanded=True):
            test_comment = st.text_area(
                "Enter test comment:",
                placeholder="Type a comment to test AI response..."
            )
            test_platform = st.selectbox(
                "Platform:",
                ["instagram", "youtube", "facebook", "linkedin", "twitter"]
            )
            
            if st.button("Generate Test Reply"):
                if test_comment:
                    with st.spinner("Generating AI reply..."):
                        result = processors['ai'].test_reply_generation(
                            test_comment, test_platform
                        )
                        
                        # Display results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Classification:**")
                            st.write(f"Type: `{result['classification']['type']}`")
                            st.write(f"Confidence: {result['classification']['metadata']['confidence']:.2%}")
                            
                            st.write("**Sentiment:**")
                            st.write(f"Sentiment: {result['sentiment']['sentiment']}")
                            st.write(f"Score: {result['sentiment']['score']:.2f}")
                        
                        with col2:
                            st.write("**Generated Reply:**")
                            st.info(result['reply'])
                            
                            if result.get('triggers', {}).get('workflows'):
                                st.write("**GHL Triggers:**")
                                st.write(f"Tags: {', '.join(result['triggers']['tags'])}")
                                st.write(f"Workflows: {', '.join(result['triggers']['workflows'])}")
    
    # Get comments from database
    db = get_db()
    start_time, end_time = get_time_range(time_range)
    
    comments = crud_comment.get_filtered(
        db,
        platforms=platforms,
        comment_types=comment_types,
        time_range=(start_time, end_time) if start_time else None,
        limit=50
    )
    
    if not comments:
        st.info("No comments found. They'll appear here as they come in! 🎯")
    else:
        # Group by platform
        for platform in platforms:
            platform_comments = [c for c in comments if c.platform == platform]
            if platform_comments:
                st.markdown(f"### {get_platform_icon(platform)} {platform.upper()}")
                
                for comment in platform_comments[:10]:
                    with st.container():
                        # Get post info
                        post = crud_post.get(db, comment.post_id) if comment.post_id else None
                        
                        # Comment card
                        comment_html = f"""
                        <div class='comment-card'>
                            <div style='display: flex; justify-content: space-between; align-items: center;'>
                                <div>
                                    <strong>{comment.author}</strong>
                                    <span style='color: #666; font-size: 0.875rem; margin-left: 10px;'>
                                        {time_ago(comment.published_at)}
                                    </span>
                                </div>
                                <div>
                                    <span class='platform-badge {platform}'>{platform}</span>
                                    <span class='status-badge status-{comment.comment_type or "general"}'>
                                        {comment.comment_type or "general"}
                                    </span>
                                </div>
                            </div>
                            <p style='margin-top: 10px;'>{comment.content}</p>
                            {f"<small style='color: #666;'>On: {truncate_text(post.content or '', 50)}</small>" if post else ""}
                        </div>
                        """
                        st.markdown(comment_html, unsafe_allow_html=True)
                        
                        # Action buttons
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                        
                        with col1:
                            if comment.has_reply:
                                st.success("✅ Replied")
                            else:
                                st.warning("⏳ Pending")
                        
                        with col2:
                            if not comment.has_reply and st.button("🤖 AI Reply", key=f"ai_{comment.id}"):
                                with st.spinner("Generating..."):
                                    comment_data = {
                                        "id": comment.id,
                                        "platform": comment.platform,
                                        "platform_comment_id": comment.platform_comment_id,
                                        "content": comment.content,
                                        "author": comment.author,
                                        "post_id": comment.post_id
                                    }
                                    result = processors['comment'].process_comment(db, comment_data)
                                    st.success("AI reply generated!")
                                    time.sleep(0.5)
                                    st.rerun()
                        
                        with col3:
                            if st.button("👁️ Details", key=f"view_{comment.id}"):
                                st.session_state[f"show_details_{comment.id}"] = True
                        
                        # Show details if requested
                        if st.session_state.get(f"show_details_{comment.id}"):
                            with st.expander("Comment Details", expanded=True):
                                st.json({
                                    "id": comment.id,
                                    "platform_id": comment.platform_comment_id,
                                    "sentiment": comment.sentiment,
                                    "confidence": comment.confidence,
                                    "metadata": comment.metadata
                                })
    
    db.close()

# Tab 2: AI Reply Queue
with tab2:
    st.subheader("🤖 AI Generated Replies - Pending Approval")
    
    db = get_db()
    pending_replies = crud_reply.get_pending(db, limit=50)
    
    if not pending_replies:
        st.success("No pending replies. All caught up! 🎉")
    else:
        # Bulk approve button
        if st.button("✅ Approve All Visible", key="bulk_approve"):
            approved = 0
            for reply in pending_replies:
                if processors['comment'].approve_reply(db, reply.id, "bulk_manual"):
                    approved += 1
            st.success(f"Approved {approved} replies!")
            time.sleep(0.5)
            st.rerun()
        
        # Display pending replies
        for reply in pending_replies:
            comment = crud_comment.get(db, reply.comment_id)
            if not comment:
                continue
            
            with st.expander(
                f"{get_platform_icon(comment.platform)} Reply to {comment.author} - {comment.comment_type}",
                expanded=True
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("**Original Comment:**")
                    st.write(comment.content)
                    
                    st.markdown("**AI Generated Reply:**")
                    st.markdown(
                        f"<div class='ai-reply-card'>{reply.content}</div>",
                        unsafe_allow_html=True
                    )
                    
                    # Confidence and triggers
                    col_a, col_b = st.columns(2)
                    with col_a:
                        confidence = reply.confidence or 0.5
                        st.progress(confidence)
                        st.caption(f"Confidence: {confidence:.0%}")
                    
                    with col_b:
                        if reply.ghl_triggers:
                            triggers = reply.ghl_triggers
                            if triggers.get("tags"):
                                st.caption(f"Tags: {', '.join(triggers['tags'])}")
                            if triggers.get("workflows"):
                                st.caption(f"Workflows: {len(triggers['workflows'])}")
                
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button("✅ Approve", key=f"approve_{reply.id}", type="primary"):
                        if processors['comment'].approve_reply(db, reply.id):
                            st.success("Approved!")
                            time.sleep(0.5)
                            st.rerun()
                    
                    if st.button("❌ Reject", key=f"reject_{reply.id}"):
                        if processors['comment'].reject_reply(db, reply.id):
                            st.warning("Rejected")
                            time.sleep(0.5)
                            st.rerun()
                    
                    if st.button("✏️ Edit", key=f"edit_{reply.id}"):
                        st.session_state[f"editing_{reply.id}"] = True
                
                # Edit mode
                if st.session_state.get(f"editing_{reply.id}"):
                    edited_reply = st.text_area(
                        "Edit reply:",
                        value=reply.content,
                        key=f"edit_text_{reply.id}"
                    )
                    if st.button("💾 Save", key=f"save_edit_{reply.id}"):
                        crud_reply.update(db, reply.id, {"content": edited_reply})
                        st.success("Reply updated!")
                        st.session_state[f"editing_{reply.id}"] = False
                        st.rerun()
    
    db.close()

# Tab 3: Content Generator
with tab3:
    st.subheader("📝 AI Content Generator")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        content_type = st.selectbox(
            "Content Type",
            list(processors['content'].content_templates.keys()),
            format_func=lambda x: processors['content'].content_templates[x]['description']
        )
        
        topic = st.text_input(
            "Topic/Theme",
            placeholder="e.g., faith and resilience, morning motivation"
        )
        
        series = st.text_input(
            "Series Name (optional)",
            placeholder="e.g., Weekly Wisdom, Monday Motivation"
        )
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            count = st.number_input("How many?", min_value=1, max_value=10, value=3)
        with col_b:
            tone = st.selectbox(
                "Tone",
                ["inspirational", "educational", "conversational", "professional", "casual"]
            )
        with col_c:
            if st.button("🚀 Generate", type="primary", use_container_width=True):
                st.session_state.generate_content = True
    
    with col2:
        st.markdown("### 💡 Quick Actions")
        
        if st.button("📅 Weekly Calendar", use_container_width=True):
            st.session_state.content_action = "calendar"
            st.session_state.generate_content = True
        
        if st.button("📱 Campaign Pack", use_container_width=True):
            st.session_state.content_action = "campaign"
            st.session_state.generate_content = True
        
        if st.button("🔄 Bulk Captions", use_container_width=True):
            st.session_state.content_action = "bulk_captions"
            st.session_state.generate_content = True
    
    # Generate content
    if st.session_state.get('generate_content'):
        with st.spinner("Creating amazing content..."):
            try:
                db = get_db()
                
                if st.session_state.get('content_action') == 'calendar':
                    # Generate weekly calendar
                    calendar = processors['content'].generate_content_calendar(
                        theme=topic or "Weekly Inspiration",
                        days=7
                    )
                    st.success(f"Generated {len(calendar['content'])} pieces for your calendar!")
                    
                    # Display calendar
                    for day_content in calendar['content']:
                        with st.expander(f"Day {day_content['day']}: {day_content['subtitle']}"):
                            st.write(day_content['content'])
                            
                            # Save to database
                            crud_content.create(db, {
                                "content_type": day_content['type'],
                                "topic": day_content['topic'],
                                "series": calendar['theme'],
                                "content": day_content['content'],
                                "hashtags": day_content.get('hashtags', []),
                                "status": "draft",
                                "metadata": day_content['metadata']
                            })
                
                elif st.session_state.get('content_action') == 'campaign':
                    # Generate campaign content
                    campaign = processors['content'].generate_campaign_content(
                        campaign_name=topic or "New Campaign",
                        platforms=["instagram", "facebook", "youtube", "email"]
                    )
                    st.success("Campaign content generated!")
                    
                    for platform, contents in campaign['content'].items():
                        st.markdown(f"### {get_platform_icon(platform)} {platform.upper()}")
                        for content in contents:
                            with st.expander(content['type']):
                                st.write(content['content'])
                                
                                # Save to database
                                crud_content.create(db, {
                                    "content_type": content['type'],
                                    "topic": content['topic'],
                                    "series": content.get('series'),
                                    "content": content['content'],
                                    "hashtags": content.get('hashtags', []),
                                    "status": "draft",
                                    "metadata": {**content['metadata'], "platform": platform}
                                })
                
                else:
                    # Normal content generation
                    generated = processors['content'].generate_content(
                        content_type=content_type,
                        topic=topic,
                        series=series,
                        count=count,
                        tone=tone
                    )
                    
                    st.success(f"Generated {len(generated)} pieces of content!")
                    
                    for i, item in enumerate(generated):
                        with st.expander(f"{content_type} #{i+1}"):
                            st.write(item['content'])
                            
                            if item.get('hashtags'):
                                st.caption(f"Hashtags: {' '.join(item['hashtags'])}")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("💾 Save", key=f"save_content_{i}"):
                                    crud_content.create(db, {
                                        "content_type": item['type'],
                                        "topic": item['topic'],
                                        "series": item.get('series'),
                                        "content": item['content'],
                                        "hashtags": item.get('hashtags', []),
                                        "status": "draft",
                                        "metadata": item['metadata']
                                    })
                                    st.success("Saved!")
                            
                            with col2:
                                if st.button("📋 Copy", key=f"copy_content_{i}"):
                                    st.write("Copied to clipboard!")
                                    st.code(item['content'])
                            
                            with col3:
                                if st.button("🔄 Regenerate", key=f"regen_content_{i}"):
                                    st.session_state.regenerate_index = i
                                    st.rerun()
                
                db.close()
                
            except Exception as e:
                st.error(f"Generation failed: {str(e)}")
        
        st.session_state.generate_content = False
        st.session_state.content_action = None

# Tab 4: Analytics
with tab4:
    st.subheader("📊 Performance Analytics")
    
    # Date range selector
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
    
    db = get_db()
    
    # Get analytics summary
    analytics = crud_analytics.get_summary(
        db,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""<div class='metric-card'>
                <h2>{format_number(analytics['total_comments'])}</h2>
                <p>Total Comments</p>
                <small>{get_platform_icon('youtube')} {get_platform_icon('facebook')} {get_platform_icon('instagram')}</small>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""<div class='metric-card'>
                <h2>{format_number(analytics['total_replies'])}</h2>
                <p>AI Replies</p>
                <small>🤖 Auto-generated</small>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""<div class='metric-card'>
                <h2>{analytics['response_rate']:.1f}%</h2>
                <p>Response Rate</p>
                <small>📈 Engagement</small>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col4:
        total_ghl = db.query(crud_ghl.model).filter(
            crud_ghl.model.status == "executed"
        ).count()
        st.markdown(
            f"""<div class='metric-card'>
                <h2>{format_number(total_ghl)}</h2>
                <p>GHL Actions</p>
                <small>🎯 Triggered</small>
            </div>""",
            unsafe_allow_html=True
        )
    
    # Charts
    st.markdown("### 📈 Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Platform breakdown
        if analytics.get('platform_breakdown'):
            fig_platform = px.pie(
                values=list(analytics['platform_breakdown'].values()),
                names=[get_platform_icon(p) + " " + p.title() for p in analytics['platform_breakdown'].keys()],
                title="Comments by Platform",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_platform.update_traces(textposition='inside', textinfo='percent+label')
            fig_platform.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig_platform, use_container_width=True)
    
    with col2:
        # Comment types
        if analytics.get('comment_types'):
            # Sort by count
            sorted_types = sorted(
                analytics['comment_types'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            fig_types = px.bar(
                x=[x[1] for x in sorted_types],
                y=[x[0].title() for x in sorted_types],
                orientation='h',
                title="Comment Types Distribution",
                color=[x[0] for x in sorted_types],
                color_discrete_map={
                    "lead": "#ff9800",
                    "praise": "#4caf50",
                    "question": "#2196f3",
                    "complaint": "#f44336",
                    "spam": "#9e9e9e",
                    "general": "#607d8b"
                }
            )
            fig_types.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                showlegend=False,
                xaxis_title="Count",
                yaxis_title=""
            )
            st.plotly_chart(fig_types, use_container_width=True)
    
    # Time series chart
    st.markdown("### 📅 Daily Activity")
    
    # Get daily metrics
    daily_comments = []
    daily_replies = []
    dates = []
    
    current_date = start_date
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())
        
        comment_count = db.query(crud_comment.model).filter(
            crud_comment.model.created_at >= day_start,
            crud_comment.model.created_at <= day_end
        ).count()
        
        reply_count = db.query(crud_reply.model).filter(
            crud_reply.model.created_at >= day_start,
            crud_reply.model.created_at <= day_end,
            crud_reply.model.status == "posted"
        ).count()
        
        dates.append(current_date)
        daily_comments.append(comment_count)
        daily_replies.append(reply_count)
        
        current_date += timedelta(days=1)
    
    fig_timeline = go.Figure()
    
    fig_timeline.add_trace(go.Scatter(
        x=dates,
        y=daily_comments,
        mode='lines+markers',
        name='Comments',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    
    fig_timeline.add_trace(go.Scatter(
        x=dates,
        y=daily_replies,
        mode='lines+markers',
        name='AI Replies',
        line=dict(color='#2ca02c', width=3),
        marker=dict(size=8)
    ))
    
    fig_timeline.update_layout(
        title="Daily Activity Trend",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Top performing content
    st.markdown("### 🏆 Top Performing Content")
    
    # Get posts with most comments
    top_posts = db.query(
        crud_post.model,
        db.func.count(crud_comment.model.id).label('comment_count')
    ).join(
        crud_comment.model
    ).group_by(
        crud_post.model.id
    ).order_by(
        db.desc('comment_count')
    ).limit(5).all()
    
    for post, count in top_posts:
        with st.expander(f"{get_platform_icon(post.platform)} {truncate_text(post.content or 'Untitled', 50)} - {count} comments"):
            st.write(f"**Platform:** {post.platform}")
            st.write(f"**Published:** {post.published_at.strftime('%Y-%m-%d %H:%M') if post.published_at else 'Unknown'}")
            st.write(f"**Comments:** {count}")
            if post.url:
                st.markdown(f"[View Post]({post.url})")
    
    db.close()

# Tab 5: GHL Actions
with tab5:
    st.subheader("⚡ GoHighLevel Integration")
    
    db = get_db()
    
    # GHL connection status
    if settings.ghl_api_key:
        st.success("✅ GHL Connected")
    else:
        st.warning("⚠️ GHL API Key not configured")
        st.info("Add your GHL API key in the .env file to enable integration")
    
    # Recent GHL actions
    st.markdown("### 🎯 Recent Actions")
    
    recent_actions = db.query(crud_ghl.model).order_by(
        crud_ghl.model.created_at.desc()
    ).limit(20).all()
    
    if not recent_actions:
        st.info("No GHL actions yet. They'll appear here when comments trigger workflows.")
    else:
        for action in recent_actions:
            comment = crud_comment.get(db, action.comment_id)
            if comment:
                with st.expander(
                    f"{action.action_type} - {comment.author} - {time_ago(action.created_at)}",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Action:** {action.action_type}")
                        st.write(f"**Contact ID:** {action.contact_id}")
                        if action.tags:
                            st.write(f"**Tags:** {', '.join(action.tags)}")
                        if action.workflow_name:
                            st.write(f"**Workflow:** {action.workflow_name}")
                    
                    with col2:
                        st.write(f"**Status:** {action.status}")
                        st.write(f"**Created:** {action.created_at.strftime('%Y-%m-%d %H:%M')}")
                        if action.executed_at:
                            st.write(f"**Executed:** {action.executed_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    st.markdown("**Original Comment:**")
                    st.write(comment.content)
    
    # Workflow statistics
    st.markdown("### 📊 Workflow Statistics")
    
    workflow_stats = db.query(
        crud_ghl.model.workflow_name,
        db.func.count(crud_ghl.model.id).label('count')
    ).filter(
        crud_ghl.model.workflow_name.isnot(None)
    ).group_by(
        crud_ghl.model.workflow_name
    ).all()
    
    if workflow_stats:
        df_workflows = pd.DataFrame(workflow_stats, columns=['Workflow', 'Count'])
        fig_workflows = px.bar(
            df_workflows,
            x='Count',
            y='Workflow',
            orientation='h',
            title="Triggered Workflows",
            color='Count',
            color_continuous_scale='Blues'
        )
        fig_workflows.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig_workflows, use_container_width=True)
    
    db.close()

# Footer
st.markdown("---")
st.markdown(
    "<center>Built with ❤️ for Ervin | AI-Powered Social Media Management</center>",
    unsafe_allow_html=True
)

# Auto-refresh logic
if st.session_state.auto_refresh:
    time.sleep(10)
    st.rerun()
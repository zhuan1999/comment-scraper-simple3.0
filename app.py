import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from datetime import datetime
from io import BytesIO
import os

# 页面配置
st.set_page_config(
    page_title="Shopee评论爬取器",
    page_icon="🛍️",
    layout="wide"
)

# 自定义CSS
st.markdown("""
<style>
    .stButton > button {
        background-color: #ee4d2d;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
    }
    .stButton > button:hover {
        background-color: #d83b1f;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 应用标题
st.title("🛍️ Shopee评论爬取工具")
st.markdown("使用Selenium自动化技术获取Shopee商品评论")

def setup_chrome_driver():
    """设置Chrome浏览器驱动"""
    try:
        chrome_options = Options()
        
        # 无头模式选项
        headless = st.session_state.get('headless', True)
        if headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 绕过自动化检测
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 添加User-Agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 启动浏览器
        driver = webdriver.Chrome(options=chrome_options)
        
        # 执行CDP命令绕过检测
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return driver
    
    except Exception as e:
        st.error(f"启动Chrome浏览器失败: {str(e)}")
        return None

def extract_reviews_from_page(driver, url, max_reviews=50):
    """从页面提取评论"""
    reviews = []
    
    try:
        # 访问页面
        st.info(f"正在访问: {url}")
        driver.get(url)
        time.sleep(3)
        
        # 获取页面标题
        page_title = driver.title
        st.info(f"页面标题: {page_title}")
        
        # 获取页面HTML
        html = driver.page_source
        
        # 方法1：直接搜索评论相关内容
        st.info("正在搜索评论...")
        
        # 查找所有包含星号(★)的元素
        all_elements = driver.find_elements(By.TAG_NAME, "div")
        
        review_count = 0
        for element in all_elements:
            try:
                text = element.text.strip()
                if not text:
                    continue
                
                # 判断是否为评论（包含星号且有一定长度）
                if '★' in text and len(text) > 20:
                    # 解析评论
                    review_data = parse_review_text(text)
                    if review_data:
                        reviews.append(review_data)
                        review_count += 1
                        
                        # 显示前几个评论
                        if review_count <= 3:
                            with st.expander(f"评论 {review_count}", expanded=False):
                                st.write(f"**用户**: {review_data['用户名']}")
                                st.write(f"**评分**: {review_data['评分']}星")
                                st.write(f"**时间**: {review_data['时间']}")
                                st.write(f"**内容**: {review_data['评论内容'][:200]}...")
                        
                        if review_count >= max_reviews:
                            break
                            
            except:
                continue
        
        # 如果没有找到评论，尝试滚动页面
        if review_count == 0:
            st.info("正在滚动页面加载更多内容...")
            
            # 滚动页面多次
            for i in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 再次查找
                all_elements = driver.find_elements(By.TAG_NAME, "div")
                for element in all_elements[-100:]:  # 只检查新加载的内容
                    try:
                        text = element.text.strip()
                        if '★' in text and len(text) > 20:
                            review_data = parse_review_text(text)
                            if review_data:
                                reviews.append(review_data)
                                review_count += 1
                    except:
                        continue
                
                if review_count >= max_reviews:
                    break
        
        return reviews
    
    except Exception as e:
        st.error(f"提取评论失败: {str(e)}")
        return reviews

def parse_review_text(text):
    """解析评论文本"""
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) < 2:
            return None
        
        # 提取用户名（通常是第一行的开始部分）
        first_line = lines[0]
        username_match = re.match(r'^([a-zA-Z0-9_*]+)', first_line)
        username = username_match.group(1) if username_match else "匿名用户"
        
        # 提取评分（通过★的数量）
        stars = first_line.count('★')
        rating = min(stars, 5)
        
        # 提取日期
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        date_match = None
        review_time = "未知时间"
        
        for line in lines:
            match = re.search(date_pattern, line)
            if match:
                review_time = match.group(1)
                break
        
        # 提取评论内容
        comment_lines = []
        for line in lines:
            # 跳过用户名行、日期行、产品变体行
            if line.startswith(username) or re.match(date_pattern, line) or 'Variation:' in line:
                continue
            # 跳过卖家回复
            if 'Seller' in line or 'Selleker' in line:
                break
            # 添加到评论内容
            if line and len(line) > 2:
                comment_lines.append(line)
        
        comment = ' '.join(comment_lines[:3])  # 只取前3行
        
        # 提取产品变体
        variation = ""
        for line in lines:
            if 'Variation:' in line:
                variation = line.replace('Variation:', '').strip()
                break
        
        return {
            '用户名': username,
            '时间': review_time,
            '评分': rating,
            '评论内容': comment,
            '产品变体': variation,
            '原始文本': text[:200]  # 保存部分原始文本用于调试
        }
        
    except Exception as e:
        return None

def main():
    """主函数"""
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 配置选项")
        
        # 商品URL输入
        default_url = "https://shopee.co.id/Glad2Glow-Moisturizer-Series-Mencerahkan-Pencerah-Wajah-Anti-Jerawat-Penuaan-Hilangkan-Flek-Tenangkan-Kulit-Niacinamide-377-Retinol-Centella-Skincare-Pelembab-Esensi-Perawatan-Kulit-day-cream-tone-up-g2g-official-store-i.809769142.42800295602"
        product_url = st.text_input("商品链接", value=default_url)
        
        # 爬取设置
        st.subheader("爬取设置")
        max_reviews = st.slider("最大评论数", 10, 200, 50, 10)
        
        # 显示选项
        st.subheader("显示选项")
        show_browser = st.checkbox("显示浏览器窗口", value=False)
        
        if show_browser:
            st.session_state.headless = False
        else:
            st.session_state.headless = True
        
        st.markdown("---")
        
        # 开始爬取按钮
        if st.button("🚀 开始爬取", type="primary", use_container_width=True):
            if product_url:
                st.session_state.scrape_url = product_url
                st.session_state.scrape_max = max_reviews
                st.session_state.start_scrape = True
            else:
                st.error("请输入商品链接")
    
    # 主界面
    if st.session_state.get('start_scrape', False):
        product_url = st.session_state.scrape_url
        max_reviews = st.session_state.scrape_max
        
        st.header(f"正在爬取评论...")
        
        # 显示爬取信息
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"目标评论数: {max_reviews}")
        with col2:
            st.info(f"显示浏览器: {'是' if not st.session_state.headless else '否'}")
        
        # 进度条
        progress_bar = st.progress(0)
        
        # 执行爬取
        with st.spinner("正在启动浏览器..."):
            driver = setup_chrome_driver()
            
            if driver:
                try:
                    # 更新进度
                    progress_bar.progress(20)
                    
                    # 提取评论
                    reviews = extract_reviews_from_page(driver, product_url, max_reviews)
                    
                    # 更新进度
                    progress_bar.progress(80)
                    
                    # 关闭浏览器
                    driver.quit()
                    
                    # 更新进度
                    progress_bar.progress(100)
                    
                    # 处理结果
                    if reviews:
                        # 转换为DataFrame
                        df = pd.DataFrame(reviews)
                        
                        # 显示成功信息
                        st.success(f"✅ 成功获取 {len(df)} 条评论！")
                        
                        # 显示统计信息
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            avg_rating = df['评分'].mean()
                            st.metric("平均评分", f"{avg_rating:.1f} ⭐")
                        with col2:
                            st.metric("评论总数", len(df))
                        with col3:
                            today_reviews = df[df['时间'].str.contains(datetime.now().strftime('%Y-%m-%d'))].shape[0]
                            st.metric("今日评论", today_reviews)
                        
                        # 显示数据表格
                        st.subheader("📋 评论数据")
                        st.dataframe(
                            df[['用户名', '时间', '评分', '评论内容']],
                            use_container_width=True,
                            hide_index=True,
                            height=400
                        )
                        
                        # 评分分布
                        st.subheader("📊 评分分布")
                        rating_counts = df['评分'].value_counts().sort_index()
                        st.bar_chart(rating_counts)
                        
                        # 导出功能
                        st.subheader("💾 导出数据")
                        
                        # CSV格式
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 下载CSV文件",
                            data=csv,
                            file_name=f"shopee_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # 显示原始数据（用于调试）
                        with st.expander("查看原始数据（前5条）"):
                            for i, review in enumerate(df.head(5).to_dict('records')):
                                st.markdown(f"""
                                **评论 {i+1}**
                                ```text
                                {review['原始文本']}
                                ```
                                """)
                        
                    else:
                        st.error("未找到评论数据")
                        st.markdown("""
                        ### 可能的原因：
                        1. 商品可能没有评论
                        2. 页面结构可能发生了变化
                        3. 网络连接问题
                        
                        ### 建议：
                        1. 手动打开商品页面确认是否有评论
                        2. 尝试其他商品链接
                        3. 稍后重试
                        """)
                        
                except Exception as e:
                    st.error(f"爬取过程中出错: {str(e)}")
                    if driver:
                        driver.quit()
            else:
                st.error("无法启动Chrome浏览器")
    
    else:
        # 显示使用说明
        st.markdown("""
        ### 🎯 使用说明
        
        1. **在侧边栏输入商品链接**
           - 复制Shopee商品页面的完整URL
           - 或者使用默认的示例链接
        
        2. **配置爬取选项**
           - 设置要爬取的最大评论数
           - 选择是否显示浏览器窗口
        
        3. **开始爬取**
           - 点击"开始爬取"按钮
           - 等待爬取完成
           - 查看和导出数据
        
        ### 📝 示例商品链接格式：
        ```
        https://shopee.co.id/商品名称-i.店铺ID.商品ID
        ```
        
        ### ⚠️ 注意事项：
        - 首次运行可能需要一些时间启动浏览器
        - 爬取速度取决于网络连接
        - 请遵守Shopee的使用条款
        
        ### 🔧 技术信息：
        - 使用Selenium自动化浏览器
        - 支持动态加载内容
        - 自动解析评论格式
        """)

if __name__ == "__main__":
    # 初始化session状态
    if 'start_scrape' not in st.session_state:
        st.session_state.start_scrape = False
    if 'headless' not in st.session_state:
        st.session_state.headless = True
    
    main()

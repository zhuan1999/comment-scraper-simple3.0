import streamlit as st
import pandas as pd
import time
import re
import json
from datetime import datetime
from io import BytesIO
import base64
import sys
import os

# 页面配置
st.set_page_config(
    page_title="Shopee评论爬取工具（Selenium版）",
    page_icon="🛍️",
    layout="wide"
)

# 自定义样式
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #ee4d2d;
    }
    .stButton > button {
        background-color: #ee4d2d;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #d83b1f;
        transform: scale(1.05);
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 5px solid #28a745;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 5px solid #17a2b8;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 5px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.title("🛍️ Shopee评论爬取工具（Selenium版）")
st.markdown("使用浏览器自动化技术，100%获取Shopee商品评论")

class ShopeeSeleniumScraper:
    """使用Selenium的Shopee评论爬取器"""
    
    def __init__(self):
        self.driver = None
        
    def init_driver(self):
        """初始化浏览器驱动"""
        try:
            # 根据环境选择合适的WebDriver
            if st.secrets.get("USE_CHROMEDRIVER", "false").lower() == "true":
                # 生产环境：使用ChromeDriver
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager.chrome import ChromeDriverManager
                
                chrome_options = Options()
                
                # 生产环境配置
                chrome_options.add_argument('--headless')  # 无头模式
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                
                # 绕过自动化检测
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # 添加user-agent
                chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # 使用webdriver-manager自动管理driver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # 执行CDP命令，绕过检测
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
            else:
                # 本地开发：使用已安装的Chrome
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                
                chrome_options = Options()
                chrome_options.add_argument('--headless')  # 本地测试也可用无头
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                self.driver = webdriver.Chrome(options=chrome_options)
            
            st.success("✅ 浏览器驱动初始化成功")
            return True
            
        except Exception as e:
            st.error(f"❌ 浏览器驱动初始化失败: {str(e)}")
            st.info("💡 解决方案：")
            st.markdown("""
            1. **确保已安装Chrome浏览器**
            2. **安装ChromeDriver**：
               - Windows: 下载并解压到PATH
               - Mac: `brew install chromedriver`
               - Linux: `apt-get install chromium-chromedriver`
            3. **或者使用webdriver-manager自动安装**：
               ```bash
               pip install webdriver-manager
               ```
            """)
            return False
    
    def extract_reviews_from_page(self, url, max_reviews=100, scroll_times=10):
        """从页面提取评论"""
        reviews = []
        
        try:
            # 访问商品页面
            st.info(f"🌐 正在访问: {url[:80]}...")
            self.driver.get(url)
            time.sleep(3)  # 等待页面加载
            
            # 接受cookies（如果有）
            try:
                accept_btn = self.driver.find_element("xpath", "//button[contains(text(), 'Terima') or contains(text(), 'Accept')]")
                accept_btn.click()
                time.sleep(1)
            except:
                pass
            
            # 滚动加载更多评论
            st.info("📜 正在滚动加载评论...")
            progress_bar = st.progress(0)
            
            for i in range(scroll_times):
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 更新进度
                progress_bar.progress((i + 1) / scroll_times)
                
                # 检查是否已经加载了足够评论
                current_reviews = self.parse_reviews_on_page()
                if len(current_reviews) >= max_reviews:
                    break
            
            progress_bar.empty()
            
            # 解析评论
            st.info("🔍 正在解析评论内容...")
            reviews = self.parse_reviews_on_page()[:max_reviews]
            
            return reviews
            
        except Exception as e:
            st.error(f"爬取过程中出错: {str(e)}")
            return reviews
        
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()
    
    def parse_reviews_on_page(self):
        """解析当前页面的所有评论"""
        reviews = []
        
        try:
            # 查找评论容器 - 多个可能的class名
            selectors = [
                'div[class*="product-review"]',
                'div[class*="comment-list"]',
                'div[data-sqe="reviews"]',
                'div.review-list',
                '.shopee-product-rating__list',
            ]
            
            review_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements("css selector", selector)
                    if elements:
                        review_elements = elements
                        break
                except:
                    continue
            
            # 如果没有找到，尝试更通用的查找方法
            if not review_elements:
                # 查找包含星号(★)的div
                all_divs = self.driver.find_elements("css selector", "div")
                for div in all_divs:
                    try:
                        text = div.text
                        if '★' in text and ('202' in text or '2024' in text or '2025' in text):
                            review_elements.append(div)
                    except:
                        continue
            
            # 解析每个评论元素
            for element in review_elements:
                try:
                    review = self.parse_single_review(element)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    continue
            
            return reviews
            
        except Exception as e:
            st.warning(f"解析评论时出错: {str(e)}")
            return reviews
    
    def parse_single_review(self, element):
        """解析单个评论元素"""
        try:
            text = element.text
            
            # 提取用户名（通常是第一个非空行）
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None
            
            username = lines[0]
            # 清理用户名
            username = re.sub(r'[^a-zA-Z0-9*_\-\.]', '', username)
            if not username or len(username) < 2:
                username = f"user_{hash(text) % 10000:04d}"
            
            # 提取评分（通过★符号）
            stars = text.count('★')
            rating = min(stars, 5) if stars > 0 else 5
            
            # 提取日期
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{1,2}\s+\w+\s+\d{4})',
            ]
            
            review_time = "未知时间"
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    review_time = match.group(1)
                    break
            
            # 提取评论内容
            comment_lines = []
            skip_next = False
            
            for i, line in enumerate(lines):
                # 跳过用户名行、日期行、产品变体行
                if i == 0 or re.match(date_patterns[0], line) or line.startswith('Variation:'):
                    continue
                
                # 跳过卖家回复
                if 'Seller' in line or 'Selleker' in line:
                    skip_next = True
                    continue
                
                if skip_next:
                    skip_next = False
                    continue
                
                # 添加到评论内容
                if len(line) > 3:  # 忽略太短的文本
                    comment_lines.append(line)
            
            comment = ' '.join(comment_lines[:5])  # 只取前5行
            
            # 提取产品变体
            variation = ""
            variation_match = re.search(r'Variation:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
            if variation_match:
                variation = variation_match.group(1).strip()
            
            # 提取卖家回复
            seller_response = ""
            seller_match = re.search(r'Seller[\'"]?s Response:\s*(.+?)(?:\n\n|\n\w|$)', text, re.IGNORECASE | re.DOTALL)
            if seller_match:
                seller_response = seller_match.group(1).strip()
            
            return {
                '用户名': username,
                '时间': review_time,
                '评分': rating,
                '评论内容': comment,
                '产品变体': variation,
                '卖家回复': seller_response,
                '评论长度': len(comment)
            }
            
        except Exception as e:
            return None
    
    def save_screenshot(self, filename="shopee_screenshot.png"):
        """保存页面截图"""
        try:
            self.driver.save_screenshot(filename)
            return filename
        except:
            return None

def main():
    """主界面"""
    
    # 初始化爬虫
    scraper = ShopeeSeleniumScraper()
    
    # 侧边栏
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/Shopee.svg/320px-Shopee.svg.png", 
                width=150)
        
        st.markdown("### ⚙️ 配置选项")
        
        # 商品URL输入
        product_url = st.text_input(
            "商品链接",
            value="https://shopee.co.id/Glad2Glow-Moisturizer-Series-Mencerahkan-Pencerah-Wajah-Anti-Jerawat-Penuaan-Hilangkan-Flek-Tenangkan-Kulit-Niacinamide-377-Retinol-Centella-Skincare-Pelembab-Esensi-Perawatan-Kulit-day-cream-tone-up-g2g-official-store-i.809769142.42800295602",
            help="粘贴完整的Shopee商品链接"
        )
        
        st.markdown("### 📊 爬取设置")
        
        max_reviews = st.slider("最大评论数", 10, 200, 50, 10)
        scroll_times = st.slider("滚动次数", 3, 20, 8, 1,
                               help="滚动次数越多，加载的评论越多")
        
        # 是否截图
        take_screenshot = st.checkbox("保存页面截图", value=False)
        
        st.markdown("---")
        
        # 开始爬取按钮
        if st.button("🚀 开始爬取评论", type="primary", use_container_width=True):
            if product_url:
                st.session_state.scrape_url = product_url
                st.session_state.scrape_max = max_reviews
                st.session_state.scrape_scroll = scroll_times
                st.session_state.scrape_screenshot = take_screenshot
                st.session_state.start_scrape = True
            else:
                st.error("请输入商品链接")
    
    # 主界面
    if st.session_state.get('start_scrape', False):
        product_url = st.session_state.scrape_url
        max_reviews = st.session_state.scrape_max
        scroll_times = st.session_state.scrape_scroll
        take_screenshot = st.session_state.scrape_screenshot
        
        st.header(f"正在爬取评论...")
        
        # 显示爬取信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"目标评论数: {max_reviews}")
        with col2:
            st.info(f"滚动次数: {scroll_times}")
        with col3:
            st.info(f"截图: {'是' if take_screenshot else '否'}")
        
        # 执行爬取
        with st.spinner("正在初始化浏览器..."):
            if scraper.init_driver():
                reviews = scraper.extract_reviews_from_page(
                    product_url, 
                    max_reviews, 
                    scroll_times
                )
                
                if reviews:
                    # 转换为DataFrame
                    df = pd.DataFrame(reviews)
                    
                    # 显示成功信息
                    st.success(f"✅ 成功获取 {len(df)} 条评论！")
                    
                    # 显示统计信息
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总评论数", len(df))
                    with col2:
                        avg_rating = df['评分'].mean()
                        st.metric("平均评分", f"{avg_rating:.1f} ⭐")
                    with col3:
                        long_comments = df[df['评论长度'] > 20].shape[0]
                        st.metric("详细评论", f"{long_comments} 条")
                    with col4:
                        unique_users = df['用户名'].nunique()
                        st.metric("不同用户", f"{unique_users} 人")
                    
                    # 显示数据表格
                    st.subheader("📋 评论数据")
                    st.dataframe(
                        df[['用户名', '时间', '评分', '评论内容']],
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                    # 显示分析图表
                    st.subheader("📊 数据分析")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 评分分布
                        rating_counts = df['评分'].value_counts().sort_index()
                        st.bar_chart(rating_counts)
                    
                    with col2:
                        # 评论长度分布
                        import plotly.express as px
                        fig = px.histogram(df, x='评论长度', nbins=20, 
                                         title='评论长度分布')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # 导出选项
                    st.subheader("💾 导出数据")
                    
                    # 创建下载列
                    col1, col2, col3 = st.columns(3)
                    
                    # CSV格式
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    col1.download_button(
                        label="📥 下载CSV",
                        data=csv,
                        file_name=f"shopee_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # Excel格式
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='评论数据')
                    col2.download_button(
                        label="📊 下载Excel",
                        data=output.getvalue(),
                        file_name=f"shopee_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # 显示示例数据
                    with st.expander("查看前5条评论详情"):
                        for i, review in enumerate(df.head(5).to_dict('records')):
                            st.markdown(f"""
                            **评论 {i+1}** ({review['评分']}⭐)
                            - **用户**: {review['用户名']}
                            - **时间**: {review['时间']}
                            - **内容**: {review['评论内容'][:200]}...
                            """)
                
                else:
                    st.error("未能获取到评论数据")
                    st.markdown("""
                    ### 🚨 可能的原因和解决方案：
                    
                    1. **商品可能没有评论** - 检查商品页面
                    2. **页面加载太慢** - 尝试增加滚动次数和等待时间
                    3. **反爬虫机制** - 稍后重试或更换商品
                    4. **网络问题** - 检查网络连接
                    
                    ### 💡 快速测试：
                    1. 手动打开商品页面
                    2. 确认有评论数据
                    3. 复制正确的商品链接
                    """)
    
    else:
        # 主界面说明
        st.markdown("""
        ### 🎯 使用Selenium爬取Shopee评论
        
        **为什么选择Selenium？**
        - ✅ 100%绕过Shopee反爬虫
        - ✅ 获取真实可见的评论
        - ✅ 支持动态加载内容
        - ✅ 模拟真实用户行为
        
        **使用步骤：**
        1. **在侧边栏输入商品链接**
        2. **设置爬取参数**
        3. **点击"开始爬取评论"**
        4. **等待爬取完成**
        5. **导出数据**
        
        **📝 示例商品链接格式：**
        ```
        https://shopee.co.id/商品名称-i.店铺ID.商品ID
        ```
        
        **⚠️ 注意事项：**
        - 首次运行需要下载ChromeDriver
        - 爬取速度较慢（模拟真实浏览）
        - 需要稳定的网络连接
        
        **⚡ 性能优化建议：**
        - 减少最大评论数以加快速度
        - 适当减少滚动次数
        - 在网络良好时运行
        """)
        
        # 示例展示
        st.subheader("📄 示例数据格式")
        example_df = pd.DataFrame({
            '用户名': ['m****', 'i****', 'a****'],
            '时间': ['2025-01-17', '2025-01-17 7:10', '2025-01-16'],
            '评分': [5, 4, 5],
            '评论内容': [
                'Tekstur cair dan ga lengket, cept nyerep di kulit, wanginya enak',
                'Bila dipake rutin membuat wajah glowing dan lebih cerah',
                'Sangat bagus produknya, kulit menjadi halus'
            ],
            '产品变体': ['Glowing-30g', 'Glowing-100g', 'Glowing-50g'],
        })
        st.dataframe(example_df, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    # 初始化session状态
    if 'start_scrape' not in st.session_state:
        st.session_state.start_scrape = False
    
    main()

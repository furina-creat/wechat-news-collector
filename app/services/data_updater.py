"""
数据自动更新器 - 每次生成唯一标题的内容
"""
import sys, os, random, threading, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
from app import create_app, db
from app.models import NewsArticle, NewsSource

CONTENT_POOL = {
    '考公考研': [
        "考研备考是一项系统工程，需要合理规划复习时间。建议将备考分为三个阶段：基础阶段（3-6月）打牢知识基础，强化阶段（7-9月）重点突破薄弱环节，冲刺阶段（10-12月）全真模拟训练。每个阶段都要制定详细的学习计划，坚持每日复盘总结和错题整理。",
        "行测考试时间紧、题量大，合理分配答题时间至关重要。建议按照先易后难的顺序作答：先做资料分析和言语理解（得分率高），再做判断推理和数量关系（拉开差距），最后做常识判断（快速作答）。每道题的平均作答时间控制在50秒以内，要果断放弃难题。",
        "申论考试是公务员考试的重头戏，考察综合分析能力和文字表达能力。备考时要多读官方文件和政策解读，积累规范表达。作答时注意审题准确、论点鲜明、论据充实、结构完整，注意字迹工整和卷面整洁。",
        "考研英语阅读占据总分40%，是拉开分数差距的关键。提高阅读能力需要长期积累：每天精读1篇真题文章，分析长难句结构和出题思路；每周泛读2-3篇外刊文章，扩大词汇量和背景知识。阅读理解的核心是定位法和排除法。",
        "考研数学公式繁多、题型灵活，建议建立错题本和公式卡片。高数占比最大（约56%），线代（约22%）和概率（约22%）次之。核心考点包括极限与连续、导数与微分、积分学、级数、矩阵运算、特征值与特征向量等，需要系统练习。",
        "政治科目的复习要注重理解而非死记硬背。建议结合时政热点学习理论知识，建立知识点之间的逻辑联系。多做历年真题，熟悉出题风格和答题规范。分析题作答要条理清晰、层次分明，每个要点独立成段，注意理论与实际的结合。",
        "考研复试是决定录取的关键环节。复试通常包括专业课笔试、英语口语面试和综合面试。建议提前了解目标院校的复试形式和历年真题，准备自我介绍和研究计划。面试时注意仪表仪态，展现自信和真诚。",
        "公务员面试主要采用结构化面试形式，考官根据预设问题对考生进行考察。常见题型包括综合分析类、组织管理类、人际关系类和应急应变类。答题时要条理清晰、层次分明，结合自身经历和岗位需求进行阐述。",
    ],
    '应届求职': [
        "校招季通常分为秋招（9-11月）和春招（次年3-5月）两轮。秋招岗位最多、质量最高，建议提前3个月开始准备：完善简历、刷笔试题、模拟面试。重点关注目标企业的官网和校园招聘公众号，及时获取招聘动态，不要错过网申截止日期。",
        "简历是求职的第一块敲门砖。HR平均浏览一份简历的时间只有6秒，因此简历要做到重点突出、版面清晰、内容精准。使用STAR法则（情境-任务-行动-结果）描述项目经历，用数据量化工作成果，避免空泛的主观描述和冗长的段落。",
        "群面（无领导小组讨论）是很多大厂面试的重要环节。群面考察的是团队协作能力、逻辑思维能力和表达能力。在讨论中要找准自己的定位，既不要沉默不语也不要过于强势，展现出良好的团队合作精神和解决问题的能力。",
        "技术面试通常分为基础知识考察和算法编程两部分。基础知识包括计算机网络、操作系统、数据库、设计模式等核心科目。算法题建议提前刷LeetCode或牛客网，重点关注数组、链表、树、动态规划、字符串等高频题型，做到熟练掌握。",
        "面试中的行为面试题考察的是个人的软实力和价值观。常见问题包括如何处理团队冲突、如何应对挫折、举例说明领导力等。建议提前准备3-5个真实案例，按照STAR法则组织回答，突出个人特质和解决问题的能力。",
        "拿到offer后的薪资谈判是很多应届生的难题。建议提前了解行业薪资水平，不要先报出自己的底线。谈判时要着眼于总包而非月薪，保持礼貌和职业的态度。如果有多个offer可以作为谈判筹码，但不要捏造不存在的offer进行施压。",
        "秋招offer选择时，除了薪资还要考虑行业前景、公司平台、岗位发展空间、团队氛围、工作地点等因素。建议列出优先级，综合评估后做出决定。不要因为一时的高薪而忽视长期发展，也不要因为贪图安逸而放弃成长机会。",
        "实习经历是校招中最重要的加分项之一。建议在校期间争取2-3段高质量实习，每段实习时间不少于3个月。实习期间要主动承担任务、善于总结反思、与同事建立良好关系，争取获得推荐信或return offer。",
    ]
}

TITLE_PREFIXES = {
    '考公考研': [
        "考研资讯", "备考指南", "考试动态", "复习策略", "真题解析",
        "时政热点", "院校信息", "专业分析", "分数线", "调剂信息",
        "复试技巧", "面试经验", "复习规划", "考点精讲", "每日一练",
    ],
    '应届求职': [
        "校招动态", "面试技巧", "简历优化", "行业分析", "薪资报告",
        "职场心得", "招聘信息", "笔试攻略", "offer选择", "实习经验",
        "职业规划", "技能提升", "公司推荐", "岗位解析", "求职故事",
    ],
}

class DataUpdater:
    def __init__(self, interval_minutes=10):
        self.interval = interval_minutes
    
    def generate_one(self, category):
        now = datetime.now()
        prefix = random.choice(TITLE_PREFIXES[category])
        content = random.choice(CONTENT_POOL[category])
        # 标题加时间戳确保唯一
        timestamp = now.strftime("%m.%d")
        hour_min = now.strftime("%H:%M")
        title = f"{prefix} - {timestamp} ({hour_min})"
        
        app = create_app()
        with app.app_context():
            # 使用全站RSS源作为文章来源
            sources = NewsSource.query.filter_by(source_type='RSS').all()
            if not sources:
                return False
            src = random.choice(sources)
            
            # 检查防止重复（理论上标题带时间戳不会重复）
            if NewsArticle.query.filter_by(title=title).first():
                return False
            
            # 根据来源生成对应的搜索URL（让不同文章链向不同网站）
            SEARCH_URLS = {
                '澎湃新闻': 'https://www.thepaper.cn/search?keyword=',
                '新浪新闻': 'https://search.sina.com.cn/?q=',
                '新浪财经': 'https://search.sina.com.cn/?q=',
                '新浪科技': 'https://search.sina.com.cn/?q=',
                '新浪教育': 'https://search.sina.com.cn/?q=',
                '果壳网': 'https://www.guokr.com/search?q=',
                '腾讯科技': 'https://s.tencent.com/result?q=',
                '网易科技': 'https://tech.163.com/special/',
                '虎嗅': 'https://www.huxiu.com/m/search/',
            }
            base_url = SEARCH_URLS.get(src.name, 'https://www.zhihu.com/search?type=content&q=')
            search_url = base_url + title[:20]
            article = NewsArticle(
                title=title,
                content=content,
                url=search_url,
                publish_time=now - timedelta(minutes=random.randint(1, 30)),
                author='系统',
                source_site=src.name,
                source_id=src.id,
                collected_at=now
            )
            db.session.add(article)
            db.session.commit()
            return True
    
    def generate_batch(self, count=2):
        added = 0
        cats = list(TITLE_PREFIXES.keys())
        for _ in range(count):
            cat = random.choice(cats)
            if self.generate_one(cat):
                added += 1
        return added
    
    def start_background(self, app):
        def loop():
            while True:
                time.sleep(self.interval * 60)
                added = self.generate_batch(2)
                now = datetime.now().strftime('%H:%M:%S')
                print(f"[{now}] 自动更新: 新增 {added} 篇文章")
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        print(f"✅ 数据自动更新器已启动（每{self.interval}分钟）")

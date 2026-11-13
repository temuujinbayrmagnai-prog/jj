import http.server
import socketserver
import json
import sqlite3

# ==========================================
# 站点 3：集成 SQL 数据库 (SQLite)
# ==========================================
DB_NAME = 'evaluation.db'

def init_db():
    """初始化数据库并插入作业提供的初始数据"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 建表：Section 和 Response
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Section (
            id INTEGER PRIMARY KEY,
            course_name TEXT,
            enrolled_count INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Response (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            score INTEGER,
            date TEXT
        )
    ''')
    
    # 插入题目给定的初始数据（仅在表为空时插入）
    cursor.execute('SELECT COUNT(*) FROM Section')
    if cursor.fetchone()[0] == 0:
        sections = [(1, 'Programming', 10), (2, 'Networks', 8), (3, 'Databases', 6)]
        cursor.executemany('INSERT INTO Section VALUES (?, ?, ?)', sections)
        
        responses = [
            (1, 1, 5, "2023-10-01"), (2, 1, 4, "2023-10-01"), (3, 1, 3, "2023-10-01"),
            (4, 1, 4, "2023-10-01"), (5, 1, 4, "2023-10-01"),
            (6, 2, 5, "2023-10-02"), (7, 2, 3, "2023-10-02")
        ]
        cursor.executemany('INSERT INTO Response (section_id, score, date) VALUES (?, ?, ?)', responses)
        conn.commit()
    conn.close()

def execute_sql_reports():
    """执行站点 3 要求的 SQL 查询并打印"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("【站点 3 需求 1：显示每个区块的回复数量和平均分】")
    sql1 = '''
        SELECT s.id, s.course_name, COUNT(r.id) AS response_count, AVG(r.score) AS average_score
        FROM Section s
        LEFT JOIN Response r ON s.id = r.section_id
        GROUP BY s.id, s.course_name
    '''
    cursor.execute(sql1)
    for row in cursor.fetchall():
        avg = f"{row[3]:.2f}" if row[3] is not None else "NULL"
        print(f"Section {row[0]} ({row[1]}): 回复数={row[2]}, 平均分={avg}")
        
    print("\n【站点 3 需求 2：计算每个区块的参与百分比】")
    sql2 = '''
        SELECT s.id, s.course_name, (COUNT(r.id) * 100.0) / s.enrolled_count AS participation_percentage
        FROM Section s
        LEFT JOIN Response r ON s.id = r.section_id
        GROUP BY s.id, s.course_name, s.enrolled_count
    '''
    cursor.execute(sql2)
    for row in cursor.fetchall():
        print(f"Section {row[0]} ({row[1]}): 参与率={row[2]:.2f}%")
    print("="*50 + "\n")
    conn.close()

def get_web_data():
    """从数据库获取用于网页展示的数据"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 由于表格要求显示课程名，我们将 Response 和 Section 连接起来
    cursor.execute('''
        SELECT s.course_name, r.score, r.date 
        FROM Response r 
        JOIN Section s ON r.section_id = s.id
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # 转换为 JSON 格式的字典列表，并模拟姓名
    data = []
    for i, row in enumerate(rows):
        data.append({"name": f"Student_{i+1}", "course": row[0], "score": row[1], "date": row[2]})
    return data

def insert_db_data(course, score, date):
    """将网页表单提交的数据插入 SQL 数据库"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 如果课程不存在，自动新增一个 Section
    cursor.execute('SELECT id FROM Section WHERE course_name = ?', (course,))
    res = cursor.fetchone()
    if res:
        section_id = res[0]
    else:
        cursor.execute('INSERT INTO Section (course_name, enrolled_count) VALUES (?, 10)', (course,))
        section_id = cursor.lastrowid
    
    cursor.execute('INSERT INTO Response (section_id, score, date) VALUES (?, ?, ?)', (section_id, score, date))
    conn.commit()
    conn.close()


# 初始化数据库并执行一次报告打印
init_db()
execute_sql_reports()

# ==========================================
# 站点 5：Web 界面 (HTML/JS)
# ==========================================
HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Grade Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; padding: 15px; background-color: #f4f7f6; margin: 0; }
        .container { max-width: 950px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #333; }
        .form-group { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; padding: 10px; background: #eef2f5; border-radius: 5px; align-items: center; }
        input, select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 8px 15px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #218838; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #007BFF; color: white; }
        .msg { color: green; font-weight: bold; display: none; }
        
        @media (max-width: 768px) {
            table, thead, tbody, th, td, tr { display: block; }
            th { position: absolute; top: -9999px; left: -9999px; }
            tr { border: 1px solid #ccc; margin-bottom: 10px; }
            td { border: none; border-bottom: 1px solid #eee; position: relative; padding-left: 50%; }
            td:before { position: absolute; left: 6px; font-weight: bold; }
            td:nth-of-type(1):before { content: "Name"; }
            td:nth-of-type(2):before { content: "Course"; }
            td:nth-of-type(3):before { content: "Score"; }
            td:nth-of-type(4):before { content: "Grade"; }
            td:nth-of-type(5):before { content: "Date"; }
        }
    </style>
</head>
<body>
<div class="container">
    <h2>🎓 Student Grade Management (SQL Backend)</h2>
    
    <div class="form-group">
        <span>Add Record:</span>
        <input type="text" id="addName" placeholder="Student Name">
        <input type="text" id="addCourse" placeholder="Course">
        <input type="number" id="addScore" placeholder="Score" min="0" max="100">
        <input type="date" id="addDate">
        <button onclick="addGrade()">Submit</button>
        <span id="msgBox" class="msg">Added to SQL Database!</span>
    </div>

    <div class="form-group" style="background:#fff; border: 1px solid #ddd;">
        <input type="text" id="searchInput" placeholder="Search..." oninput="renderDashboard()">
        <select id="gradeFilter" onchange="renderDashboard()">
            <option value="">All Grades</option>
            <option value="A">A</option><option value="B">B</option>
            <option value="C">C</option><option value="D">D</option><option value="F">F</option>
        </select>
        <input type="number" id="minScore" placeholder="Min Score" oninput="renderDashboard()" style="width: 100px;">
        <input type="number" id="maxScore" placeholder="Max Score" oninput="renderDashboard()" style="width: 100px;">
    </div>

    <table>
        <thead>
            <tr><th>Student Name</th><th>Course</th><th>Score</th><th>Grade</th><th>Exam Date</th></tr>
        </thead>
        <tbody id="tableBody"></tbody>
    </table>

    <h3>📊 Average Scores by Course</h3>
    <div id="chartContainer" style="width: 100%; height: 350px;"></div>
</div>

<script>
    let globalData = [];
    let myChart = null;

    function getLetterGrade(score) {
        if (score >= 90) return 'A'; if (score >= 80) return 'B';
        if (score >= 70) return 'C'; if (score >= 60) return 'D';
        return 'F';
    }

    async function fetchData() {
        try {
            const response = await fetch('/api/data');
            globalData = await response.json();
            renderDashboard();
        } catch (error) {
            document.getElementById('tableBody').innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">No data available</td></tr>';
        }
    }

    async function addGrade() {
        const name = document.getElementById('addName').value;
        const course = document.getElementById('addCourse').value;
        const score = parseFloat(document.getElementById('addScore').value);
        const date = document.getElementById('addDate').value;

        if (!name || !course || isNaN(score) || !date) {
            alert("Please fill in all fields correctly.");
            return;
        }

        // 将数据发送给 Python 后端存入 SQL 数据库
        await fetch('/api/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course: course, score: score, date: date })
        });

        const msg = document.getElementById('msgBox');
        msg.style.display = 'inline';
        setTimeout(() => { msg.style.display = 'none'; }, 3000);
        
        document.getElementById('addName').value = '';
        document.getElementById('addCourse').value = '';
        document.getElementById('addScore').value = '';
        document.getElementById('addDate').value = '';

        // 重新从数据库拉取最新数据刷新页面
        fetchData();
    }

    function renderDashboard() {
        const tbody = document.getElementById('tableBody');
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const gradeFilter = document.getElementById('gradeFilter').value;
        const minScore = parseFloat(document.getElementById('minScore').value) || 0;
        const maxScore = parseFloat(document.getElementById('maxScore').value) || 100;

        tbody.innerHTML = '';
        
        const filtered = globalData.filter(row => {
            const matchSearch = row.name.toLowerCase().includes(searchTerm) || row.course.toLowerCase().includes(searchTerm);
            const letter = getLetterGrade(row.score);
            const matchGrade = gradeFilter === "" || letter === gradeFilter;
            const matchScoreRange = row.score >= minScore && row.score <= maxScore;
            return matchSearch && matchGrade && matchScoreRange;
        });
        
        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #888;">No data available</td></tr>';
        } else {
            filtered.forEach(row => {
                const letter = getLetterGrade(row.score);
                let color = letter === 'F' ? 'red' : (letter === 'A' ? 'green' : 'orange');
                tbody.innerHTML += `<tr>
                    <td>${row.name}</td><td>${row.course}</td>
                    <td>${row.score}</td><td style="color:${color}; font-weight:bold;">${letter}</td>
                    <td>${row.date}</td>
                </tr>`;
            });
        }
        updateChart(globalData);
    }

    function updateChart(data) {
        if (!myChart) myChart = echarts.init(document.getElementById('chartContainer'));
        const courseData = {};
        data.forEach(item => {
            if (!courseData[item.course]) courseData[item.course] = { total: 0, count: 0 };
            courseData[item.course].total += item.score;
            courseData[item.course].count += 1;
        });
        const courses = Object.keys(courseData);
        const averages = courses.map(c => (courseData[c].total / courseData[c].count).toFixed(1));
        myChart.setOption({
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: courses },
            yAxis: { type: 'value', max: 100 },
            series: [{ data: averages, type: 'bar', itemStyle: { color: '#007BFF' }, label: { show: true, position: 'top' } }]
        });
    }

    window.onload = fetchData;
</script>
</body>
</html>
"""

# ==========================================
# 后端服务器代码
# ==========================================
class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            data_list = get_web_data()
            self.wfile.write(json.dumps(data_list, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)
            
    def do_POST(self):
        if self.path == '/api/add':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 将新数据写入 SQL 数据库
            insert_db_data(data['course'], data['score'], data['date'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        else:
            self.send_error(404)

def run_server():
    PORT = 8000
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), MyRequestHandler) as httpd:
            print(f"✅ 运行成功！请在浏览器访问: http://localhost:{PORT}")
            print("按 Ctrl+C 停止服务器。")
            httpd.serve_forever()
    except Exception as e:
        print(f"启动失败: {e}")

if __name__ == '__main__':
    run_server()
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>自动询价系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h2 { margin-bottom: 15px; color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 500; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        button { background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; font-size: 14px; }
        button:hover { background: #5568d3; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; font-size: 14px; margin-top: 5px; }
        .features { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .feature { background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .feature h3 { font-size: 16px; margin-bottom: 5px; }
        .feature p { color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 自动询价系统</h1>
        <p>三渠道综合询价：网页 / 厂家 / 历史</p>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">150</div>
                <div class="stat-label">历史记录</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">23</div>
                <div class="stat-label">产品种类</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">62</div>
                <div class="stat-label">Python文件</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 产品询价</h2>
            <div class="form-group">
                <label>产品名称</label>
                <input type="text" id="product" placeholder="输入产品名称，如：网络摄像机">
            </div>
            <div class="form-group">
                <label>品牌</label>
                <input type="text" id="brand" placeholder="可选，如：海康威视">
            </div>
            <button onclick="search()">🔍 查询</button>
            
            <div id="results" style="margin-top: 20px;">
                <table id="resultTable" style="display: none;">
                    <thead>
                        <tr>
                            <th>产品</th>
                            <th>品牌</th>
                            <th>价格</th>
                            <th>来源</th>
                        </tr>
                    </thead>
                    <tbody id="resultBody"></tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h2>✨ 功能特性</h2>
            <div class="features">
                <div class="feature">
                    <h3>🔍 三渠道询价</h3>
                    <p>网页抓取 / 厂家邮件 / 历史数据</p>
                </div>
                <div class="feature">
                    <h3>📧 邮件闭环</h3>
                    <p>发送询价 → 收取回复 → 自动提取</p>
                </div>
                <div class="feature">
                    <h3>📊 智能报告</h3>
                    <p>Markdown / HTML 双格式</p>
                </div>
                <div class="feature">
                    <h3>📈 可视化</h3>
                    <p>价格图表 + HTML仪表板</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 模拟数据
        const mockData = [
            { name: '网络摄像机', brand: '海康威视', price: 850, source: '京东' },
            { name: '网络摄像机', brand: '海康威视', price: 780, source: '渠道商' },
            { name: '硬盘录像机', brand: '海康威视', price: 2950, source: '天猫' },
            { name: '监控硬盘', brand: '希捷', price: 1250, source: '京东' },
            { name: '核心交换机', brand: '华为', price: 5800, source: '京东' },
        ];
        
        function search() {
            const product = document.getElementById('product').value.toLowerCase();
            const brand = document.getElementById('brand').value.toLowerCase();
            
            let results = mockData;
            if (product) {
                results = results.filter(r => r.name.toLowerCase().includes(product));
            }
            if (brand) {
                results = results.filter(r => r.brand.toLowerCase().includes(brand));
            }
            
            const tbody = document.getElementById('resultBody');
            tbody.innerHTML = '';
            
            if (results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#666;">未找到匹配结果</td></tr>';
            } else {
                results.forEach(r => {
                    tbody.innerHTML += `<tr>
                        <td>${r.name}</td>
                        <td>${r.brand}</td>
                        <td style="color:#e74c3c;font-weight:bold;">¥${r.price.toLocaleString()}</td>
                        <td>${r.source}</td>
                    </tr>`;
                });
            }
            
            document.getElementById('resultTable').style.display = 'table';
        }
    </script>
</body>
</html>

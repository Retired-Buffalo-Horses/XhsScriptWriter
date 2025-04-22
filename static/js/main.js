// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask应用前端脚本已加载');
    
    // 添加导航栏活跃状态
    highlightCurrentPage();
    
    // 添加平滑滚动效果
    setupSmoothScroll();
    
    // 设置移动端菜单切换
    setupMobileMenu();
    
    // 添加页面加载动画
    const main = document.querySelector('main');
    if (main) {
        main.style.opacity = '0';
        setTimeout(() => {
            main.style.transition = 'opacity 0.5s ease';
            main.style.opacity = '1';
        }, 100);
    }
});

// 高亮当前页面的导航链接
function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-menu a');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// 设置平滑滚动
function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// 设置移动端菜单
function setupMobileMenu() {
    const navbarToggle = document.getElementById('navbar-toggle');
    const navbarMenu = document.getElementById('navbar-menu');
    
    if (navbarToggle && navbarMenu) {
        navbarToggle.addEventListener('click', function() {
            navbarMenu.classList.toggle('active');
            
            // 点击菜单项后自动关闭菜单
            const menuItems = navbarMenu.querySelectorAll('a');
            menuItems.forEach(item => {
                item.addEventListener('click', function() {
                    navbarMenu.classList.remove('active');
                });
            });
        });
        
        // 点击页面其他区域关闭菜单
        document.addEventListener('click', function(event) {
            if (!navbarToggle.contains(event.target) && !navbarMenu.contains(event.target)) {
                navbarMenu.classList.remove('active');
            }
        });
    }
}

// 添加当前年份到页脚
const footerYear = document.querySelector('footer p');
if (footerYear) {
    const yearText = footerYear.textContent;
    footerYear.textContent = yearText.replace('{{ now.year }}', new Date().getFullYear());
} 
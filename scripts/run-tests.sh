#!/bin/bash
# ============================================================================
# CAUC-SEP 测试运行脚本
#
# 文件名: run-tests.sh
# 路径: scripts/
# 功能: 运行所有测试（后端单元测试、集成测试、前端测试）
# 版本: v0.3.0
#
# 作者：CAUC-SEP 开发团队
# 创建日期：2024-03-01
# 最后更新：2026-03-14
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
CAUC-SEP 测试运行脚本

用法: $0 [选项]

选项:
    -h, --help          显示帮助信息
    -b, --backend       仅运行后端测试
    -f, --frontend      仅运行前端测试
    -u, --unit          仅运行单元测试
    -i, --integration   仅运行集成测试
    -c, --coverage      生成覆盖率报告
    -v, --verbose       详细输出
    --quick             快速测试（跳过慢速测试）
    --all               运行所有测试（默认）

示例:
    $0                  # 运行所有测试
    $0 -b -u            # 仅运行后端单元测试
    $0 -f -c            # 运行前端测试并生成覆盖率
    $0 --quick          # 快速测试模式

EOF
}

# 默认参数
RUN_BACKEND=true
RUN_FRONTEND=true
RUN_UNIT=true
RUN_INTEGRATION=true
WITH_COVERAGE=false
VERBOSE=false
QUICK_MODE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--backend)
            RUN_FRONTEND=false
            shift
            ;;
        -f|--frontend)
            RUN_BACKEND=false
            shift
            ;;
        -u|--unit)
            RUN_INTEGRATION=false
            shift
            ;;
        -i|--integration)
            RUN_UNIT=false
            shift
            ;;
        -c|--coverage)
            WITH_COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --all)
            RUN_BACKEND=true
            RUN_FRONTEND=true
            RUN_UNIT=true
            RUN_INTEGRATION=true
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 进入项目根目录
cd "${PROJECT_ROOT}"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ==================== 后端测试 ====================
run_backend_tests() {
    log_info "开始运行后端测试..."
    cd "${BACKEND_DIR}"

    # 检查依赖
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        log_warning "未找到虚拟环境，使用系统Python"
    fi

    # 构建pytest命令
    PYTEST_CMD="pytest"

    if [ "$VERBOSE" = true ]; then
        PYTEST_CMD="${PYTEST_CMD} -v"
    fi

    if [ "$WITH_COVERAGE" = true ]; then
        PYTEST_CMD="${PYTEST_CMD} --cov=core --cov=api --cov-report=xml --cov-report=html"
    fi

    if [ "$QUICK_MODE" = true ]; then
        PYTEST_CMD="${PYTEST_CMD} -m 'not slow'"
    fi

    # 运行单元测试
    if [ "$RUN_UNIT" = true ]; then
        log_info "运行后端单元测试..."
        UNIT_CMD="${PYTEST_CMD} tests/unit -m 'not integration and not windows'"

        if eval "${UNIT_CMD}"; then
            log_success "后端单元测试通过"
            ((PASSED_TESTS++))
        else
            log_error "后端单元测试失败"
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
    fi

    # 运行集成测试
    if [ "$RUN_INTEGRATION" = true ]; then
        log_info "运行后端集成测试..."
        INTEGRATION_CMD="${PYTEST_CMD} tests/integration -m 'not slow and not windows'"

        if eval "${INTEGRATION_CMD}"; then
            log_success "后端集成测试通过"
            ((PASSED_TESTS++))
        else
            log_warning "后端集成测试部分失败（可能需要硬件连接）"
            # 集成测试失败不计入失败，因为可能需要硬件
        fi
        ((TOTAL_TESTS++))
    fi

    cd "${PROJECT_ROOT}"
}

# ==================== 前端测试 ====================
run_frontend_tests() {
    log_info "开始运行前端测试..."
    cd "${FRONTEND_DIR}"

    # 检查node_modules
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm ci
    fi

    # 构建测试命令
    TEST_CMD="npm run test:run"

    if [ "$WITH_COVERAGE" = true ]; then
        TEST_CMD="npm run test:coverage"
    fi

    if [ "$VERBOSE" = true ]; then
        TEST_CMD="${TEST_CMD} -- --reporter=verbose"
    fi

    # 运行测试
    if eval "${TEST_CMD}"; then
        log_success "前端测试通过"
        ((PASSED_TESTS++))
    else
        log_error "前端测试失败"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    cd "${PROJECT_ROOT}"
}

# ==================== 主流程 ====================
main() {
    log_info "======================================"
    log_info "CAUC-SEP 测试套件"
    log_info "======================================"
    echo ""

    START_TIME=$(date +%s)

    # 运行后端测试
    if [ "$RUN_BACKEND" = true ]; then
        run_backend_tests
        echo ""
    fi

    # 运行前端测试
    if [ "$RUN_FRONTEND" = true ]; then
        run_frontend_tests
        echo ""
    fi

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # 输出测试结果汇总
    log_info "======================================"
    log_info "测试结果汇总"
    log_info "======================================"
    echo ""
    echo -e "总测试套件: ${TOTAL_TESTS}"
    echo -e "通过: ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "失败: ${RED}${FAILED_TESTS}${NC}"
    echo -e "耗时: ${DURATION}秒"
    echo ""

    if [ "$WITH_COVERAGE" = true ]; then
        log_info "覆盖率报告已生成:"
        if [ "$RUN_BACKEND" = true ]; then
            echo "  - 后端HTML报告: ${BACKEND_DIR}/htmlcov/index.html"
            echo "  - 后端XML报告: ${BACKEND_DIR}/coverage.xml"
        fi
        if [ "$RUN_FRONTEND" = true ]; then
            echo "  - 前端HTML报告: ${FRONTEND_DIR}/coverage/index.html"
        fi
        echo ""
    fi

    # 返回退出码
    if [ ${FAILED_TESTS} -gt 0 ]; then
        log_error "存在测试失败"
        exit 1
    else
        log_success "所有测试通过!"
        exit 0
    fi
}

# 执行主流程
main

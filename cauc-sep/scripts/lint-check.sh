#!/bin/bash
# CAUC-SEP 代码检查脚本
# 用途：运行所有代码检查工具（black, isort, ruff, mypy, eslint, prettier）

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
CAUC-SEP 代码检查脚本

用法: $0 [选项]

选项:
    -h, --help          显示帮助信息
    -b, --backend       仅检查后端代码
    -f, --frontend      仅检查前端代码
    -F, --fix           自动修复问题
    -v, --verbose       详细输出
    --format            仅运行格式检查
    --lint              仅运行代码检查
    --type              仅运行类型检查
    --security          仅运行安全检查
    --all               运行所有检查（默认）

示例:
    $0                  # 运行所有检查
    $0 -b               # 仅检查后端
    $0 -F               # 自动修复问题
    $0 --format         # 仅格式检查

EOF
}

# 默认参数
RUN_BACKEND=true
RUN_FRONTEND=true
AUTO_FIX=false
VERBOSE=false
CHECK_FORMAT=true
CHECK_LINT=true
CHECK_TYPE=true
CHECK_SECURITY=true

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
        -F|--fix)
            AUTO_FIX=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --format)
            CHECK_LINT=false
            CHECK_TYPE=false
            CHECK_SECURITY=false
            shift
            ;;
        --lint)
            CHECK_FORMAT=false
            CHECK_TYPE=false
            CHECK_SECURITY=false
            shift
            ;;
        --type)
            CHECK_FORMAT=false
            CHECK_LINT=false
            CHECK_SECURITY=false
            shift
            ;;
        --security)
            CHECK_FORMAT=false
            CHECK_LINT=false
            CHECK_TYPE=false
            shift
            ;;
        --all)
            CHECK_FORMAT=true
            CHECK_LINT=true
            CHECK_TYPE=true
            CHECK_SECURITY=true
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

# 检查结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# ==================== 后端检查 ====================
run_backend_checks() {
    log_info "开始后端代码检查..."
    cd "${BACKEND_DIR}"

    # ==================== Black格式检查 ====================
    if [ "$CHECK_FORMAT" = true ]; then
        log_info "检查Black格式..."
        ((TOTAL_CHECKS++))

        if [ "$AUTO_FIX" = true ]; then
            if black . --config ../pyproject.toml; then
                log_success "Black格式化完成"
                ((PASSED_CHECKS++))
            else
                log_error "Black格式化失败"
                ((FAILED_CHECKS++))
            fi
        else
            if black --check --diff . --config ../pyproject.toml; then
                log_success "Black格式检查通过"
                ((PASSED_CHECKS++))
            else
                log_error "Black格式检查失败，请运行: black ."
                ((FAILED_CHECKS++))
            fi
        fi
    fi

    # ==================== isort导入排序检查 ====================
    if [ "$CHECK_FORMAT" = true ]; then
        log_info "检查isort导入排序..."
        ((TOTAL_CHECKS++))

        if [ "$AUTO_FIX" = true ]; then
            if isort . --settings-path ../pyproject.toml; then
                log_success "isort排序完成"
                ((PASSED_CHECKS++))
            else
                log_error "isort排序失败"
                ((FAILED_CHECKS++))
            fi
        else
            if isort --check-only --diff . --settings-path ../pyproject.toml; then
                log_success "isort检查通过"
                ((PASSED_CHECKS++))
            else
                log_error "isort检查失败，请运行: isort ."
                ((FAILED_CHECKS++))
            fi
        fi
    fi

    # ==================== Ruff代码检查 ====================
    if [ "$CHECK_LINT" = true ]; then
        log_info "运行Ruff代码检查..."
        ((TOTAL_CHECKS++))

        RUFF_CMD="ruff check . --config ../pyproject.toml"

        if [ "$AUTO_FIX" = true ]; then
            RUFF_CMD="${RUFF_CMD} --fix"
        fi

        if [ "$VERBOSE" = true ]; then
            RUFF_CMD="${RUFF_CMD} --show-fixes"
        fi

        if eval "${RUFF_CMD}"; then
            log_success "Ruff检查通过"
            ((PASSED_CHECKS++))
        else
            if [ "$AUTO_FIX" = true ]; then
                log_warning "Ruff已修复部分问题"
            else
                log_error "Ruff检查失败，请运行: ruff check . --fix"
            fi
            ((FAILED_CHECKS++))
        fi
    fi

    # ==================== MyPy类型检查 ====================
    if [ "$CHECK_TYPE" = true ]; then
        log_info "运行MyPy类型检查..."
        ((TOTAL_CHECKS++))

        MYPY_CMD="mypy --config-file ../pyproject.toml ."

        if [ "$VERBOSE" = true ]; then
            MYPY_CMD="${MYPY_CMD} --show-error-context"
        fi

        if eval "${MYPY_CMD}"; then
            log_success "MyPy类型检查通过"
            ((PASSED_CHECKS++))
        else
            log_warning "MyPy类型检查发现问题（非阻塞）"
            # MyPy问题不阻塞，因为类型检查可能需要时间完善
        fi
    fi

    # ==================== Bandit安全检查 ====================
    if [ "$CHECK_SECURITY" = true ]; then
        log_info "运行Bandit安全检查..."
        ((TOTAL_CHECKS++))

        if bandit -r . -c ../pyproject.toml -ll; then
            log_success "Bandit安全检查通过"
            ((PASSED_CHECKS++))
        else
            log_warning "Bandit发现潜在安全问题"
            ((FAILED_CHECKS++))
        fi
    fi

    cd "${PROJECT_ROOT}"
}

# ==================== 前端检查 ====================
run_frontend_checks() {
    log_info "开始前端代码检查..."
    cd "${FRONTEND_DIR}"

    # 检查node_modules
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm ci
    fi

    # ==================== ESLint检查 ====================
    if [ "$CHECK_LINT" = true ]; then
        log_info "运行ESLint检查..."
        ((TOTAL_CHECKS++))

        ESLINT_CMD="npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs"

        if [ "$AUTO_FIX" = true ]; then
            ESLINT_CMD="${ESLINT_CMD} --fix"
        fi

        if [ "$VERBOSE" = true ]; then
            ESLINT_CMD="${ESLINT_CMD} --format stylish"
        fi

        if eval "${ESLINT_CMD}"; then
            log_success "ESLint检查通过"
            ((PASSED_CHECKS++))
        else
            if [ "$AUTO_FIX" = true ]; then
                log_warning "ESLint已修复部分问题"
            else
                log_error "ESLint检查失败，请运行: npm run lint -- --fix"
            fi
            ((FAILED_CHECKS++))
        fi
    fi

    # ==================== Prettier格式检查 ====================
    if [ "$CHECK_FORMAT" = true ]; then
        log_info "运行Prettier格式检查..."
        ((TOTAL_CHECKS++))

        PRETTIER_CMD="npx prettier --check \"src/**/*.{js,vue,css,scss,json}\""

        if [ "$AUTO_FIX" = true ]; then
            PRETTIER_CMD="npx prettier --write \"src/**/*.{js,vue,css,scss,json}\""
        fi

        if eval "${PRETTIER_CMD}"; then
            log_success "Prettier格式检查通过"
            ((PASSED_CHECKS++))
        else
            if [ "$AUTO_FIX" = true ]; then
                log_success "Prettier格式化完成"
            else
                log_error "Prettier格式检查失败，请运行: npx prettier --write \"src/**/*.{js,vue,css,scss,json}\""
            fi
            ((FAILED_CHECKS++))
        fi
    fi

    cd "${PROJECT_ROOT}"
}

# ==================== 主流程 ====================
main() {
    log_info "======================================"
    log_info "CAUC-SEP 代码检查工具"
    log_info "======================================"
    echo ""

    START_TIME=$(date +%s)

    # 运行后端检查
    if [ "$RUN_BACKEND" = true ]; then
        run_backend_checks
        echo ""
    fi

    # 运行前端检查
    if [ "$RUN_FRONTEND" = true ]; then
        run_frontend_checks
        echo ""
    fi

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # 输出检查结果汇总
    log_info "======================================"
    log_info "检查结果汇总"
    log_info "======================================"
    echo ""
    echo -e "总检查项: ${TOTAL_CHECKS}"
    echo -e "通过: ${GREEN}${PASSED_CHECKS}${NC}"
    echo -e "失败: ${RED}${FAILED_CHECKS}${NC}"
    echo -e "耗时: ${DURATION}秒"
    echo ""

    # 返回退出码
    if [ ${FAILED_CHECKS} -gt 0 ]; then
        log_error "存在检查失败项"
        if [ "$AUTO_FIX" = false ]; then
            log_info "提示: 使用 -F 参数自动修复部分问题"
        fi
        exit 1
    else
        log_success "所有检查通过!"
        exit 0
    fi
}

# 执行主流程
main

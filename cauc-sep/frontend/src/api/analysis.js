/**
 * @file analysis.js
 * @path src/api/
 * @description 数据分析相关API接口封装
 * @author Agent
 * @date 2024-03-07
 * @dependencies utils/apiRequest
 */

import { post } from '../utils/apiRequest';

/**
 * 多模型拟合对比
 * 
 * @param {Object} data - 拟合数据
 * @param {Array<number>} data.h_data - 磁场强度数据
 * @param {Array<number>} data.b_data - 磁感应强度数据
 * @param {Array<string>} data.models - 选择的模型列表
 * @returns {Promise<Object>} 拟合结果
 */
export async function multiModelFit(data) {
  const result = await post('/api/v1/analysis/multi-fit', data, {
    onError: (msg) => console.error('Multi-model fit error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 生成分析报告
 * 
 * @param {Object} data - 报告数据
 * @param {Array<number>} data.h_data - 磁场强度数据
 * @param {Array<number>} data.b_data - 磁感应强度数据
 * @param {boolean} data.include_raw_data - 是否包含原始数据
 * @returns {Promise<Object>} 报告数据
 */
export async function generateAnalysisReport(data) {
  const result = await post('/api/v1/analysis/report/generate', data, {
    onError: (msg) => console.error('Generate report error:', msg)
  });

  return result.success ? result.data : null;
}

/**
 * 导出分析报告
 * 
 * @param {Object} data - 导出参数
 * @param {Array<number>} data.h_data - 磁场强度数据
 * @param {Array<number>} data.b_data - 磁感应强度数据
 * @param {string} data.format - 导出格式 (json/csv)
 * @returns {Promise<Blob>} 文件Blob对象
 */
export async function exportAnalysisReport(data) {
  try {
    const response = await fetch('/api/v1/analysis/report/export', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.blob();
  } catch (error) {
    console.error('Export report error:', error);
    throw error;
  }
}

/**
 * 获取分析历史记录
 * 
 * @returns {Array} 历史记录列表
 */
export function getAnalysisHistory() {
  try {
    const stored = localStorage.getItem('cauc_sep_analysis_history');
    return stored ? JSON.parse(stored) : [];
  } catch (error) {
    console.error('Failed to get analysis history:', error);
    return [];
  }
}

/**
 * 保存分析结果到历史记录
 * 
 * @param {Object} result - 分析结果
 * @returns {boolean} 保存是否成功
 */
export function saveAnalysisToHistory(result) {
  try {
    const history = getAnalysisHistory();
    const newRecord = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      result: result,
    };
    
    history.unshift(newRecord);
    
    // 保留最近20条记录
    const trimmedHistory = history.slice(0, 20);
    localStorage.setItem('cauc_sep_analysis_history', JSON.stringify(trimmedHistory));
    
    return true;
  } catch (error) {
    console.error('Failed to save analysis to history:', error);
    return false;
  }
}

/**
 * 删除历史记录
 * 
 * @param {number} id - 记录ID
 * @returns {boolean} 删除是否成功
 */
export function deleteAnalysisHistory(id) {
  try {
    const history = getAnalysisHistory();
    const filtered = history.filter(record => record.id !== id);
    localStorage.setItem('cauc_sep_analysis_history', JSON.stringify(filtered));
    return true;
  } catch (error) {
    console.error('Failed to delete analysis history:', error);
    return false;
  }
}

/**
 * 清空所有历史记录
 * 
 * @returns {boolean} 清空是否成功
 */
export function clearAnalysisHistory() {
  try {
    localStorage.removeItem('cauc_sep_analysis_history');
    return true;
  } catch (error) {
    console.error('Failed to clear analysis history:', error);
    return false;
  }
}

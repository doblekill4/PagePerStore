// 金山文档在线表格：供 wps_airscript.py 通过 Webhook 调用的「文档共享脚本」
//
// 一次性配置：
//   1. 打开目标表格 -> 效率 / 高级开发 -> AirScript 脚本编辑器 -> 新建「文档共享脚本」
//   2. 把本文件全部内容粘贴进去并保存
//   3. 工具栏【脚本令牌(beta)】创建 APIToken，侧栏「更多」复制 webhook 链接
//   4. 把 webhook 与 token 填到程序同目录 config.json 的 WPS 段
//
// 外部调用：POST https://www.kdocs.cn/api/v3/ide/file/<file_id>/script/<script_id>/sync_task
//   Header: AirScript-Token: <token>
//   Body:   {"Context":{"argv":{"sheet_name":"服务一店一页","rows":[[...]],"options":{}}}}
//
// options:
//   ping             true 时只返回当前最后一行，不写入任何数据
//   dedup            true 时若末尾若干行与本次数据完全一致则跳过，防定时任务重复写入
//   numeric_columns  需要转成数字的列号（从 1 开始）；默认全部按文本写入，避免订单号/手机号被改写成科学计数法
//   start_row        强制指定起始行号；不填则自动追加到最后一个非空行之后

function 列号转字母(列号) {
  let 结果 = "";
  let n = 列号;
  while (n > 0) {
    n -= 1;
    结果 = String.fromCharCode(65 + (n % 26)) + 结果;
    n = Math.floor(n / 26);
  }
  return 结果;
}

function 转二维数组(值) {
  if (!Array.isArray(值)) return [[值]];
  if (值.length === 0) return [[]];
  if (!Array.isArray(值[0])) return [值];
  return 值;
}

function 单元格非空(值) {
  return 值 !== null && 值 !== undefined && String(值).trim() !== "";
}

function 追加数据(argv) {
  const 表名 = argv.sheet_name || "服务一店一页";
  const 原始行 = argv.rows || [];
  const 选项 = argv.options || {};

  let 工作表;
  try {
    工作表 = Application.Sheets(表名);
  } catch (e) {
    return { ok: false, message: "找不到工作表: " + 表名 + "（" + e + "）" };
  }
  if (!工作表) {
    return { ok: false, message: "找不到工作表: " + 表名 };
  }

  const 已用区域 = 工作表.UsedRange;
  const 起始行号 = 已用区域.Row || 1;
  const 已用值 = 转二维数组(已用区域.Value2);

  let 最后非空下标 = -1;
  for (let i = 0; i < 已用值.length; i++) {
    for (let j = 0; j < 已用值[i].length; j++) {
      if (单元格非空(已用值[i][j])) {
        最后非空下标 = i;
        break;
      }
    }
  }
  const 自动起始行 = 起始行号 + 最后非空下标 + 1;
  const 写入起始行 = 选项.start_row ? Number(选项.start_row) : 自动起始行;
  const 最后一行 = 自动起始行 - 1;

  if (选项.ping) {
    return {
      ok: true,
      ping: true,
      sheet: 表名,
      last_row: 最后一行,
      next_row: 写入起始行,
      message: "连通正常，未写入任何数据"
    };
  }

  if (!Array.isArray(原始行) || 原始行.length === 0) {
    return { ok: false, message: "rows 为空，未写入" };
  }

  const 列数 = 原始行.reduce(function (最大, 行) {
    return Math.max(最大, Array.isArray(行) ? 行.length : 1);
  }, 0);

  const 数字列 = (选项.numeric_columns || []).map(Number);
  const 数据 = 原始行.map(function (行) {
    const 新行 = (Array.isArray(行) ? 行 : [行]).map(function (值, 下标) {
      if (值 === null || 值 === undefined) return "";
      const 文本 = String(值);
      if (数字列.indexOf(下标 + 1) >= 0 && 文本.trim() !== "" && !isNaN(Number(文本))) {
        return Number(文本);
      }
      return 文本;
    });
    while (新行.length < 列数) 新行.push("");
    return 新行;
  });

  // 幂等：定时任务重跑时，若末尾若干行与本次数据完全相同则跳过
  if (选项.dedup && 写入起始行 - 数据.length >= 1) {
    const 已有 = 转二维数组(
      工作表.Range("A" + (写入起始行 - 数据.length) + ":" + 列号转字母(列数) + (写入起始行 - 1)).Value2
    );
    const 规格化 = function (行) {
      return (Array.isArray(行) ? 行 : [行]).map(function (值) {
        return 值 === null || 值 === undefined ? "" : String(值);
      }).join("\u0001");
    };
    let 完全相同 = 已有.length === 数据.length;
    if (完全相同) {
      for (let i = 0; i < 数据.length; i++) {
        if (规格化(已有[i]) !== 规格化(数据[i])) {
          完全相同 = false;
          break;
        }
      }
    }
    if (完全相同) {
      console.log("末尾数据一致，跳过重复写入");
      return { ok: true, duplicated: true, written: 0, start_row: 写入起始行, sheet: 表名 };
    }
  }

  const 目标区域 = "A" + 写入起始行 + ":" + 列号转字母(列数) + (写入起始行 + 数据.length - 1);
  工作表.Range(目标区域).Value2 = 数据;
  console.log("已写入 " + 目标区域 + "，共 " + 数据.length + " 行");

  return {
    ok: true,
    sheet: 表名,
    range: 目标区域,
    start_row: 写入起始行,
    written: 数据.length,
    columns: 列数
  };
}

return 追加数据(Context.argv || {});

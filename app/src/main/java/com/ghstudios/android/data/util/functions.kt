package com.ghstudios.android.data.util

import com.ghstudios.android.AppSettings
import android.util.Log

/**
 * Computes the column name to allow the function to work in a specific locale
 *
 * 中文模式按 中→日→英 兜底（游戏原文为日文，避免空白）：
 *   COALESCE(NULLIF(name_zh,''), name_ja, name)
 */
fun localizeColumn(locale: String, columnName: String) = when(locale) {
    "en" -> columnName
    "zh" -> "COALESCE(NULLIF(${columnName}_zh, ''), ${columnName}_ja, $columnName)"
    else -> "${columnName}_$locale"
}

/**
 * 带表名前缀的本地化列（用于 JOIN 查询，避免歧义 / 前缀拼在函数前导致 SQL 错误）。
 * 例：localizeTableColumn("i", "name") → zh: COALESCE(NULLIF(i.name_zh,''), i.name_ja, i.name)
 */
fun localizeTableColumn(table: String, columnName: String): String =
    localizeColumn(AppSettings.dataLocale, columnName, table)

fun localizeColumn(locale: String, columnName: String, table: String): String = when(locale) {
    "en" -> "$table.$columnName"
    "zh" -> "COALESCE(NULLIF($table.${columnName}_zh, ''), $table.${columnName}_ja, $table.$columnName)"
    else -> "$table.${columnName}_$locale"
}

fun getBloated (): Boolean {
    var bloated : Boolean = AppSettings.isBloatedEnabled
    return bloated
}

fun getElementTrueRaw (): Boolean {
    var elementTrueRaw: Boolean = AppSettings.isElementTrueRawEnabled
    return elementTrueRaw
}


/**
 * Returns the localized form of the base column name for the current locale
 */
fun localizeColumn(columnName: String) = localizeColumn(AppSettings.dataLocale, columnName)

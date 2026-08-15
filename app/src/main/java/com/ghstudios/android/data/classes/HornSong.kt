package com.ghstudios.android.data.classes

/**
 * 狩猎笛旋律（来自 mhfdat.bin 狩猎笛指南文本）。
 * notesColor 为 ~Cxx 颜色码序列（逗号分隔），用于音符标色。
 */
class HornSong {
    var id: Long = 0
    var category = ""
    var name = ""
    var notes = ""
    var notesColor = ""
}

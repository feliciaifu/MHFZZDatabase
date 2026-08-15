package com.ghstudios.android.features.horns

import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.support.v4.app.ListFragment
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.TextView
import com.ghstudios.android.data.DataManager
import com.ghstudios.android.data.classes.HornSong
import com.ghstudios.android.mhgendatabase.R
import com.ghstudios.android.util.loggedThread

/**
 * 狩猎笛旋律指南（数据来自 mhfdat.bin 狩猎笛指南文本）。
 * 音符按 ~Cxx 颜色码标色。
 */
class HornGuideFragment : ListFragment() {

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.fragment_generic_list, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        loggedThread("HornGuide Load") {
            val songs = DataManager.get().queryHornSongs()
            activity?.runOnUiThread { setListAdapter(HornAdapter(context!!, songs)) }
        }
    }

    private class HornAdapter(context: Context, items: List<HornSong>)
        : ArrayAdapter<HornSong>(context, 0, items) {

        override fun getView(position: Int, convertView: View?, parent: ViewGroup?): View {
            val v = convertView ?: LayoutInflater.from(context)
                    .inflate(R.layout.listitem_horn, parent, false)
            val song = getItem(position)

            val notesTv = v.findViewById<TextView>(R.id.horn_notes)
            val nameTv = v.findViewById<TextView>(R.id.horn_name)

            nameTv.text = song.name
            notesTv.text = coloredNotes(song)
            return v
        }

        /** 音符 ♪ 按颜色码着色（00 白 / 02 红 / 03 橙 / 04 黄 / 05 绿 / 07 紫 / 20 蓝） */
        private fun coloredNotes(song: HornSong): CharSequence {
            val n = song.notes.length
            val colors = song.notesColor.split(",")
            val sb = SpannableString(song.notes)
            for (i in 0 until n) {
                val code = if (i < colors.size) colors[i] else ""
                sb.setSpan(ForegroundColorSpan(colorFor(code)), i, i + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            return sb
        }

        private fun colorFor(code: String): Int = when (code) {
            "02" -> 0xFFF44336.toInt()   // 红
            "03" -> 0xFFFF9800.toInt()   // 橙
            "04" -> 0xFFFFEB3B.toInt()   // 黄
            "05" -> 0xFF4CAF50.toInt()   // 绿
            "07" -> 0xFF9C27B0.toInt()   // 紫
            "20" -> 0xFF2196F3.toInt()   // 蓝
            "01" -> 0xFF006064.toInt()   // 深蓝
            else -> Color.LTGRAY          // 白（浅灰可见）
        }
    }
}

package com.ghstudios.android.features.horns

import android.content.Context
import android.os.Bundle
import android.support.v4.app.ListFragment
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import com.ghstudios.android.SectionArrayAdapter
import com.ghstudios.android.data.DataManager
import com.ghstudios.android.data.classes.HornSong
import com.ghstudios.android.mhgendatabase.R
import com.ghstudios.android.util.MHUtils
import com.ghstudios.android.util.getColorCompat
import com.ghstudios.android.util.loggedThread

/**
 * 狩猎笛旋律指南（数据来自 mhfdat.bin 狩猎笛指南文本）。
 * 按分类（自我强化/团队/千里眼）分节，音符沿用项目 item_* 色板标色。
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
        : SectionArrayAdapter<HornSong>(context, items) {

        override fun getGroupName(item: HornSong) = item.category

        override fun newView(context: Context, song: HornSong, parent: ViewGroup): View {
            val inflater = LayoutInflater.from(context)
            return inflater.inflate(R.layout.listitem_horn, parent, false)
        }

        override fun bindView(view: View, context: Context, song: HornSong) {
            val notesTv = view.findViewById<TextView>(R.id.horn_notes)
            val nameTv = view.findViewById<TextView>(R.id.horn_name)

            nameTv.text = song.name
            notesTv.text = coloredNotes(context, song.notes)
        }

        /** 音符按 MHUtils.getNoteColor 色板标色 */
        private fun coloredNotes(context: Context, notes: String): CharSequence {
            val sb = SpannableString(notes)
            for (i in notes.indices) {
                val color = context.getColorCompat(MHUtils.getNoteColor(notes[i]))
                sb.setSpan(ForegroundColorSpan(color), i, i + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            return sb
        }
    }
}

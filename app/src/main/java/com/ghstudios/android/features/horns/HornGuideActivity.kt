package com.ghstudios.android.features.horns

import android.os.Bundle
import android.support.v4.app.Fragment
import com.ghstudios.android.GenericActivity
import com.ghstudios.android.MenuSection
import com.ghstudios.android.mhgendatabase.R

/**
 * 狩猎笛旋律指南页面（数据来自 mhfdat.bin）。
 */
class HornGuideActivity : GenericActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setTitle(R.string.title_horns)
        super.setAsTopLevel()
    }

    override fun getSelectedSection(): Int {
        return MenuSection.HORNS
    }

    override fun createFragment(): Fragment {
        return HornGuideFragment()
    }
}

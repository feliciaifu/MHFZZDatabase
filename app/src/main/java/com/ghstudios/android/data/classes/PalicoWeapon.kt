package com.ghstudios.android.data.classes

import com.ghstudios.android.mhgendatabase.R

/**
 * Created by Joseph on 7/9/2016.
 */
class PalicoWeapon {
    var id: Long = 0
    var attackMelee: Int = 0
    var attackRanged: Int = 0
    var isBlunt: Boolean = false
    var balance: Int = 0

    var element: String? = null
    var elementMelee: Int = 0
    var elementRanged: Int = 0

    val elementEnum get() = getElementFromString(element ?: "")

    var affinityMelee: Int = 0
    var affinityRanged: Int = 0
    var defense: Int = 0
    var creation_cost: Int = 0
    var sharpness: Int = 0
    var item: Item? = null

    val balanceStringRes: Int
        get() {
            when (balance) {
                0 -> return R.string.palico_balance_0
                1 -> return R.string.palico_balance_1
                else -> return R.string.palico_balance_2
            }
        }
}

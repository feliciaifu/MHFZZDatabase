package com.ghstudios.android.features.quests

import android.os.Bundle
import android.support.v4.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ExpandableListView
import com.ghstudios.android.data.classes.QuestHub

import com.ghstudios.android.data.DataManager
import com.ghstudios.android.mhgendatabase.R

// 分组：DB stars 字面量 -> 字符串资源（getString 按 locale 取，HR/G/Level 保留英文）
private val hunterquests = arrayOf(
    "HR1" to R.string.quest_group_hr1,
    "HR2" to R.string.quest_group_hr2,
    "HR3" to R.string.quest_group_hr3,
    "HR4" to R.string.quest_group_hr4,
    "HR5" to R.string.quest_group_hr5,
    "HR6" to R.string.quest_group_hr6,
    "Exotic Quests" to R.string.quest_group_exotic
)
private val ghunterquests = arrayOf(
    "Gathering Quests" to R.string.quest_group_gathering,
    "G1" to R.string.quest_group_g1,
    "G2" to R.string.quest_group_g2,
    "G3" to R.string.quest_group_g3,
    "G4" to R.string.quest_group_g4,
    "G5" to R.string.quest_group_g5,
    "G6" to R.string.quest_group_g6,
    "G7" to R.string.quest_group_g7,
    "Burst Origin Quests" to R.string.quest_group_burst_origin,
    "G Exotic Quests" to R.string.quest_group_g_exotic
)
private val guild = arrayOf(
    "Quest Orders" to R.string.quest_group_quest_orders,
    "Training Support Quests" to R.string.quest_group_training_support
)
private val specialquests = arrayOf(
    "Superior Quests" to R.string.quest_group_superior,
    "Promotional" to R.string.quest_group_promotional,
    "Premium Quests" to R.string.quest_group_premium,
    "Paw Coins" to R.string.quest_group_paw_coins,
    "Luxury Quests" to R.string.quest_group_luxury,
    "Hiden Stone Quests" to R.string.quest_group_hidden_stone,
    "HR Ranking Rewards" to R.string.quest_group_hr_ranking
)
private val other = arrayOf(
    "Gear Acquisition Quests" to R.string.quest_group_gear_acq,
    "Hunting Technique Quests" to R.string.quest_group_hunting_tech
)
private val gspecialquests = arrayOf(
    "G Superior Quests" to R.string.quest_group_g_superior,
    "G Promotional" to R.string.quest_group_g_promotional,
    "G Hiden Stone Quests" to R.string.quest_group_g_hidden_stone
)
private val conquest = arrayOf(
    "Level 1" to R.string.quest_group_level_1,
    "Level 200" to R.string.quest_group_level_200,
    "Level 1000" to R.string.quest_group_level_1000,
    "Level 9999" to R.string.quest_group_level_9999,
    "Shiten" to R.string.quest_group_shiten,
    "Adv Shiten Quests" to R.string.quest_group_adv_shiten
)
private val event = arrayOf(
    "Low Rank" to R.string.quest_group_low_rank,
    "G Rank" to R.string.quest_group_g_rank
)



/**
 * Pieced together from: Android samples:
 * com.example.android.apis.view.ExpandableList1
 * http://androidword.blogspot.com/2012/01/how-to-use-expandablelistview.html
 * http://stackoverflow.com/questions/6938560/android-fragments-setcontentview-
 * alternative
 * http://stackoverflow.com/questions/6495898/findviewbyid-in-fragment-android
 */
class QuestExpandableListFragment : Fragment() {
    companion object {
        private val ARG_HUB = "QUEST_HUB"

        @JvmStatic fun newInstance(hub: QuestHub): QuestExpandableListFragment {
            val args = Bundle()
            args.putString(ARG_HUB, hub.toString())
            val f = QuestExpandableListFragment()
            f.arguments = args
            return f
        }
    }

    private lateinit var mHub: QuestHub
    private lateinit var groups: List<QuestGroup>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mHub = QuestHub.from(arguments?.getString(ARG_HUB) ?: "Unimplemented")
        populateList(mHub)
    }

    // todo: This logic should be moved to a viewmodel
    private fun populateList(hub: QuestHub) {
        val dataManager = DataManager.get()
        val allQuests = dataManager.queryQuestArrayHub(hub).filter {
            it.stars != "" // no zero stars (todo: filter in data manager?)
        }

        if (hub == QuestHub.PERMIT) {
            // Permit quests group by monster instead
            val monsters = dataManager.questDeviantMonsterNames()
            val groupedQuests = allQuests.groupBy { it.permitMonsterId }

            groups = groupedQuests.values.withIndex().map {
                val idx = it.index
                val quests = it.value
                //QuestGroup(monsters[idx], -1, quests) tostring
                QuestGroup(monsters[idx], "", quests)
            }

        } else {
            // Create a mapping from stars to the displayed value
            // Necessary because quests are sometimes out of order
            val labelMap = when (hub) {
                // -> village.zip(village).toMap() // village maps to self
                QuestHub.VILLAGE -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.HUNTERQUESTS -> hunterquests.toMap()
                QuestHub.GHUNTERQUESTS -> ghunterquests.toMap()
                QuestHub.SPECIALQUESTS -> specialquests.toMap()
                QuestHub.GSPECIALQUESTS -> gspecialquests.toMap()
                QuestHub.CONQUEST -> conquest.toMap()
                QuestHub.GUILD -> guild.toMap()
                QuestHub.OTHER -> other.toMap()
                QuestHub.EVENT -> event.toMap()
                QuestHub.PERMIT -> throw RuntimeException("This stretch of code can't handle Permit, unexpected error")
                QuestHub.ARENA -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.DAILY -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.GDAILY -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.GEVENT -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.GEXPERIENCE -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.GGEAR -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.INA -> throw UnsupportedOperationException("Arena is not supported")
                QuestHub.SRGUIDE -> throw UnsupportedOperationException("Arena is not supported")
            }

            // quests grouped by stars
            val groupedQuests = allQuests.groupBy { it.stars }

            // Transform to label/questlist combo, sorted by label position ascending
            groups = groupedQuests.map {
                val stars = it.key
                val quests = it.value
                //QuestGroup(labelMap[stars] ?: "", stars?.toInt() ?: -1, quests) tostring
                QuestGroup(getString(labelMap[stars] ?: R.string.quest_group_unknown), stars.toString(), quests)
            }.sortedBy { labelMap.keys.indexOf(it.stars) }

        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?,
                              savedInstanceState: Bundle?): View? {
        return inflater.inflate(R.layout.fragment_generic_expandable_list, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val elv = view.findViewById<ExpandableListView>(R.id.expandableListView)

        val type = when (mHub) {
            //QuestHub.VILLAGE -> QuestAdapterType.VILLAGE
            QuestHub.VILLAGE -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.PERMIT -> QuestAdapterType.PERMIT
            QuestHub.GUILD, QuestHub.HUNTERQUESTS, QuestHub.GHUNTERQUESTS, QuestHub.SPECIALQUESTS, QuestHub.GSPECIALQUESTS, QuestHub.OTHER, QuestHub.CONQUEST, QuestHub.EVENT -> QuestAdapterType.GUILD
            QuestHub.ARENA -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.DAILY -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.GDAILY -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.GEVENT -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.GEXPERIENCE -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.GGEAR -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.INA -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
            QuestHub.SRGUIDE -> throw UnsupportedOperationException("Arena is unsupported for expandable fragments")
        }

        elv.setAdapter(QuestListExpandableAdapter(groups, type))
    }

}
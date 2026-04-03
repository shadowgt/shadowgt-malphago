package com.malphago.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.malphago.app.ui.MalPhaGoApp
import com.malphago.app.ui.theme.MalPhaGoTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MalPhaGoTheme {
                MalPhaGoApp()
            }
        }
    }
}

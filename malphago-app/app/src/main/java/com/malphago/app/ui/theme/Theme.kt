package com.malphago.app.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val LightColorScheme = lightColorScheme(
    primary = MalPhaGoPrimary,
    onPrimary = MalPhaGoOnPrimary,
    primaryContainer = MalPhagoPrimaryContainer,
    onPrimaryContainer = MalPhaGoOnPrimaryContainer,
    secondary = MalPhaGoSecondary,
    onSecondary = MalPhaGoOnSecondary,
    secondaryContainer = MalPhaGoSecondaryContainer,
    onSecondaryContainer = MalPhaGoOnSecondaryContainer,
    tertiary = MalPhaGoTertiary,
    onTertiary = MalPhaGoOnTertiary,
    tertiaryContainer = MalPhaGoTertiaryContainer,
    onTertiaryContainer = MalPhaGoOnTertiaryContainer,
    error = MalPhaGoError,
    background = MalPhaGoBackground,
    surface = MalPhaGoSurface,
)

private val DarkColorScheme = darkColorScheme(
    primary = MalPhagoPrimaryDark,
    onPrimary = MalPhaGoOnPrimaryDark,
    primaryContainer = MalPhagoPrimaryContainerDark,
    onPrimaryContainer = MalPhaGoOnPrimaryContainerDark,
    secondary = MalPhaGoSecondaryDark,
    tertiary = MalPhaGoTertiaryDark,
    background = MalPhaGoBackgroundDark,
    surface = MalPhaGoSurfaceDark,
)

@Composable
fun MalPhaGoTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = MalPhaGoTypography,
        content = content,
    )
}

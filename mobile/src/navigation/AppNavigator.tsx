import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { createNativeStackNavigator as createLawStack } from '@react-navigation/native-stack'
import { Text, View } from 'react-native'
import { Colors } from '../theme/colors'

// Screens
import LoginScreen from '../screens/LoginScreen'
import RegisterScreen from '../screens/RegisterScreen'
import HomeScreen from '../screens/HomeScreen'
import SearchScreen from '../screens/SearchScreen'
import ChatScreen from '../screens/ChatScreen'
import LawBrowserScreen from '../screens/LawBrowserScreen'
import DieuDetailScreen from '../screens/DieuDetailScreen'
import SavedScreen from '../screens/SavedScreen'
import ProfileScreen from '../screens/ProfileScreen'
import PricingScreen from '../screens/PricingScreen'

import type {
  RootStackParamList,
  MainTabParamList,
  LawStackParamList,
} from '../types'

// ── Stacks ────────────────────────────────────────────────────────────────────

const RootStack = createNativeStackNavigator<RootStackParamList>()
const Tab = createBottomTabNavigator<MainTabParamList>()
const LawStack = createLawStack<LawStackParamList>()

// ── Law Stack Navigator ────────────────────────────────────────────────────────

function LawNavigator() {
  return (
    <LawStack.Navigator
      id="LawStack"
      screenOptions={{
        headerStyle: { backgroundColor: Colors.primary },
        headerTintColor: '#fff',
        headerTitleStyle: { fontWeight: '700', fontSize: 16 },
      }}
    >
      <LawStack.Screen
        name="LawBrowser"
        component={LawBrowserScreen}
        options={{ title: 'Hệ thống Pháp điển' }}
      />
      <LawStack.Screen
        name="DieuDetail"
        component={DieuDetailScreen}
        options={{ title: 'Chi tiết Điều luật' }}
      />
    </LawStack.Navigator>
  )
}

// ── Tab Icon helper ────────────────────────────────────────────────────────────

function TabIcon({ emoji, label, focused }: { emoji: string; label: string; focused: boolean }) {
  return (
    <View style={{ alignItems: 'center', paddingTop: 2 }}>
      <Text style={{ fontSize: 20 }}>{emoji}</Text>
      <Text
        style={{
          fontSize: 10,
          color: focused ? Colors.primary : Colors.textMuted,
          marginTop: 1,
          fontWeight: focused ? '600' : '400',
        }}
      >
        {label}
      </Text>
    </View>
  )
}

// ── Main Tab Navigator ─────────────────────────────────────────────────────────

function MainNavigator() {
  return (
    <Tab.Navigator
      id="MainTabs"
      screenOptions={{
        headerShown: false,
        tabBarShowLabel: false,
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopColor: Colors.border,
          borderTopWidth: 1,
          height: 62,
          paddingBottom: 6,
        },
      }}
    >
      <Tab.Screen
        name="HomeTab"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon emoji="🏠" label="Trang chủ" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="SearchTab"
        component={SearchScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon emoji="🔍" label="Tra cứu" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="ChatTab"
        component={ChatScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon emoji="🤖" label="Tư vấn AI" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="LawTab"
        component={LawNavigator}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon emoji="📚" label="Pháp điển" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="SavedTab"
        component={SavedScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon emoji="★" label="Đã lưu" focused={focused} />
          ),
        }}
      />
    </Tab.Navigator>
  )
}

// ── Root Navigator ─────────────────────────────────────────────────────────────

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <RootStack.Navigator id="RootStack" screenOptions={{ headerShown: false }}>
        <RootStack.Screen name="Main" component={MainNavigator} />
        <RootStack.Screen
          name="Login"
          component={LoginScreen}
          options={{ presentation: 'modal' }}
        />
        <RootStack.Screen
          name="Register"
          component={RegisterScreen}
          options={{ presentation: 'modal' }}
        />
        <RootStack.Screen
          name="Profile"
          component={ProfileScreen}
          options={{ presentation: 'card' }}
        />
        <RootStack.Screen
          name="Pricing"
          component={PricingScreen}
          options={{ presentation: 'card' }}
        />
      </RootStack.Navigator>
    </NavigationContainer>
  )
}

import React from 'react'
import { View, Text, StyleSheet, Linking, TouchableOpacity } from 'react-native'
import Markdown from 'react-native-markdown-display'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '../theme/colors'
import { Message } from '../types'

interface Props {
  message: Message
}

export default function MessageItem({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      {!isUser && (
        <View style={styles.avatar}>
          <Ionicons name="shield-checkmark" size={16} color={Colors.primary} />
        </View>
      )}

      <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
        {isUser ? (
          <Text style={styles.userText}>{message.content}</Text>
        ) : (
          <Markdown style={markdownStyles}>{message.content}</Markdown>
        )}

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <View style={styles.sources}>
            <Text style={styles.sourcesTitle}>Nguồn tham khảo:</Text>
            {message.sources.map((src, idx) => (
              <TouchableOpacity
                key={idx}
                style={styles.sourceItem}
                onPress={() => src.url && Linking.openURL(src.url)}
                activeOpacity={src.url ? 0.7 : 1}
              >
                <Text style={styles.sourceDot}>•</Text>
                <Text
                  style={[styles.sourceTitle, !!src.url && styles.sourceTitleLink]}
                  numberOfLines={2}
                >
                  {src.title}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {isUser && (
        <View style={[styles.avatar, styles.avatarUser]}>
          <Ionicons name="person" size={16} color={Colors.primary} />
        </View>
      )}
    </View>
  )
}

const markdownStyles = {
  body: { color: Colors.text, fontSize: 14, lineHeight: 20 },
  heading1: { fontSize: 18, fontWeight: '800' as const, color: Colors.dark, marginBottom: 6 },
  heading2: { fontSize: 16, fontWeight: '700' as const, color: Colors.dark, marginBottom: 4 },
  heading3: { fontSize: 14, fontWeight: '700' as const, color: Colors.dark, marginBottom: 4 },
  strong: { fontWeight: '700' as const, color: Colors.dark },
  em: { fontStyle: 'italic' as const },
  bullet_list: { marginLeft: 8 },
  ordered_list: { marginLeft: 8 },
  list_item: { marginBottom: 4, fontSize: 14, color: Colors.text },
  code_inline: {
    fontFamily: 'monospace',
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 4,
    borderRadius: 4,
    fontSize: 13,
    color: Colors.primaryDark,
  },
  fence: {
    backgroundColor: '#f3f4f6',
    borderRadius: 8,
    padding: 12,
    marginVertical: 8,
  },
  blockquote: {
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
    paddingLeft: 12,
    marginLeft: 0,
  },
  paragraph: { marginBottom: 8, fontSize: 14, color: Colors.text, lineHeight: 20 },
  link: { color: Colors.primary },
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', marginBottom: 16, paddingHorizontal: 12, gap: 8 },
  rowUser: { justifyContent: 'flex-end' },
  rowAssistant: { justifyContent: 'flex-start', alignItems: 'flex-start' },

  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: Colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
    flexShrink: 0,
  },
  avatarUser: { backgroundColor: Colors.primaryLight },

  bubble: {
    maxWidth: '80%',
    borderRadius: 14,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  bubbleUser: {
    backgroundColor: Colors.userBubble,
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: Colors.cardBg,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  userText: { color: Colors.userBubbleText, fontSize: 14, lineHeight: 20 },

  sources: {
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  sourcesTitle: { fontSize: 12, fontWeight: '700', color: Colors.textMuted, marginBottom: 6 },
  sourceItem: { flexDirection: 'row', gap: 4, marginBottom: 4 },
  sourceDot: { fontSize: 12, color: Colors.textMuted },
  sourceTitle: { flex: 1, fontSize: 12, color: Colors.textSecondary, lineHeight: 16 },
  sourceTitleLink: { color: Colors.primary, textDecorationLine: 'underline' },
})

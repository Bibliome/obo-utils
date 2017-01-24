<!--
MIT License

Copyright (c) 2017 Institut National de la Recherche Agronomique

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-->

<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0"
    >

  <xsl:param name="namespace">TRIPHASE</xsl:param>

  <xsl:output method="text"/>

  <xsl:template match="/">
    <xsl:text>format-version: 1.2&#xA;</xsl:text>
    <xsl:apply-templates select="map"/>
  </xsl:template>

  <xsl:template match="map">
    <xsl:apply-templates select="node"/>
  </xsl:template>

  <xsl:template match="node">
    <xsl:text>&#xA;[Term]&#xA;</xsl:text>
    <xsl:variable name="content">
      <xsl:choose>
	<xsl:when test="@TEXT">
	  <xsl:value-of select="normalize-space(@TEXT)"/>
	</xsl:when>
	<xsl:when test="richcontent">
	  <xsl:message>NOTE: using richcontent for <xsl:value-of select="@ID"/></xsl:message>
	  <xsl:value-of select="normalize-space(richcontent)"/>
	</xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:if test="$content = ''">
      <xsl:message>WARNING: no content found for <xsl:value-of select="@ID"/></xsl:message>
    </xsl:if>
    <xsl:value-of select="concat('id: ', $namespace, ':', substring-after(@ID, '_'), '&#xA;')"/>
    <xsl:value-of select="concat('name: ', normalize-space($content), '&#xA;')"/>
    <xsl:for-each select="parent::node">
      <xsl:value-of select="concat('is_a: ', $namespace, ':', substring-after(@ID, '_'), '&#xA;')"/>
    </xsl:for-each>
    <xsl:apply-templates select="node"/>
  </xsl:template>

</xsl:stylesheet>
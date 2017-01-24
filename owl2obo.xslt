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
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
    xmlns:atol="file:/C:/Lea/ontologies/versions%20ATOL/atol_v3.0.obo#"
    >

  <xsl:output method="text"/>
  <xsl:param name="definitions">yes</xsl:param>
  <xsl:param name="subsets"/>
  <xsl:param name="synonyms">yes</xsl:param>

  <xsl:key name="class-by-id" match="/rdf:RDF/owl:Class" use="@rdf:about"/>

  <xsl:template match="/">
    <xsl:text>format-version: 1.2&#xA;</xsl:text>
    <xsl:apply-templates select="rdf:RDF/owl:Class"/>
  </xsl:template>

  <xsl:template match="owl:Class">
    <xsl:text>&#xA;[Term]&#xA;</xsl:text>
    <xsl:choose>
      <xsl:when test="@rdf:about and rdfs:label">
	<xsl:value-of select="concat('id: ', @rdf:about, '&#xA;')"/>
	<xsl:value-of select="concat('name: ', rdfs:label, '&#xA;')"/>
	<xsl:if test="$definitions = 'yes'">
	  <xsl:apply-templates select="atol:definition"/>
	</xsl:if>
	<xsl:if test="$subsets = 'yes'">
	  <xsl:apply-templates select="atol:subsetPresent|atol:subsetAbsent"/>
	</xsl:if>
	<xsl:if test="$synonyms = 'yes'">
	  <xsl:apply-templates select="atol:synonymRelated|atol:synonymExact"/>
	</xsl:if>
	<xsl:apply-templates select="rdfs:subClassOf"/>
      </xsl:when>
      <xsl:otherwise>
	<xsl:message>class without ID or label</xsl:message>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="rdfs:subClassOf">
    <xsl:variable name="parent">
      <xsl:choose>
	<xsl:when test="@rdf:resource != ''">
	  <xsl:value-of select="@rdf:resource"/>
	</xsl:when>
	<xsl:when test="owl:Class">
	  <xsl:value-of select="owl:Class/@rdf:about"/>
	</xsl:when>
	<xsl:otherwise>
	  <xsl:message>Could not determine parent of <xsl:value-of select="parent::owl:Class/@rdf:about"/></xsl:message>
	</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="concat('is_a: ', $parent, '&#xA;')"/>
  </xsl:template>

  <xsl:template match="atol:subsetPresent|atol:subsetAbsent|atol:subsetMaybe">
    <xsl:value-of select="concat('subset: ', ., '&#xA;')"/>
  </xsl:template>

  <xsl:template match="atol:definition">
    <xsl:text>def: "</xsl:text>
    <xsl:value-of select="normalize-space(.)"/>
    <xsl:text>" []&#xA;</xsl:text>
  </xsl:template>

  <xsl:template match="atol:synonymRelated|atol:synonymExact">
    <xsl:text>synonym: "</xsl:text>
    <xsl:value-of select="normalize-space(translate(., '\', '|'))"/>
    <xsl:text>" </xsl:text>
    <xsl:choose>
      <xsl:when test="name() = 'synonymRelated'"><xsl:text>RELATED</xsl:text></xsl:when>
      <xsl:otherwise><xsl:text>EXACT</xsl:text></xsl:otherwise>
    </xsl:choose>
    <xsl:text> []&#xA;</xsl:text>
  </xsl:template>
</xsl:stylesheet>
